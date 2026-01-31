# InBody Tech-Master 배포 가이드

## 목차

1. [사전 요구 사항](#1-사전-요구-사항)
2. [환경 변수 설정](#2-환경-변수-설정)
3. [로컬 개발 환경](#3-로컬-개발-환경)
4. [Docker Compose 배포](#4-docker-compose-배포)
5. [EC2 배포](#5-ec2-배포)
6. [자동 스케줄러 (CloudFormation)](#6-자동-스케줄러-cloudformation)
7. [운영 및 모니터링](#7-운영-및-모니터링)

---

## 1. 사전 요구 사항

| 항목 | 최소 버전 |
|------|-----------|
| Python | 3.11+ |
| Docker | 24.0+ |
| Docker Compose | v2.24+ |
| AWS CLI | 2.x (EC2 배포 시) |
| Git | 2.x |

## 2. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성합니다.

```bash
cp .env.example .env
```

필수 환경 변수:

| 변수 | 설명 | 예시 |
|------|------|------|
| `OPENAI_API_KEY` | OpenAI API 키 | `sk-...` |
| `OPENAI_MODEL` | 메인 LLM 모델 | `gpt-4o` |
| `OPENAI_MINI_MODEL` | 경량 LLM 모델 | `gpt-4o-mini` |
| `CHROMA_PERSIST_DIR` | ChromaDB 저장 경로 | `./data/chroma` |
| `STRUCTURED_DB_URL` | SQLite DB 경로 | `sqlite+aiosqlite:///./data/inbody.db` |
| `LOG_LEVEL` | 로그 수준 | `INFO` |

> `.env` 파일은 `.gitignore`에 포함되어 있어 원격 저장소에 커밋되지 않습니다.

---

## 3. 로컬 개발 환경

### 3.1 의존성 설치

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 3.2 데이터 디렉토리 준비

```bash
mkdir -p data/chroma data/manuals static/images
```

### 3.3 초기 데이터 시딩

```bash
python scripts/seed_structured_data.py
python scripts/ingest_manuals.py
```

### 3.4 FastAPI 서버 실행

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

- API 문서: http://localhost:8000/docs
- 헬스체크: http://localhost:8000/api/v1/health

### 3.5 Streamlit UI 실행

별도 터미널에서 실행합니다.

```bash
API_BASE_URL=http://localhost:8000/api/v1 \
streamlit run ui/app.py --server.port=8501
```

- UI 접속: http://localhost:8501

---

## 4. Docker Compose 배포

### 4.1 아키텍처

```
┌─────────────────────────────────────────┐
│  Docker Compose                         │
│                                         │
│  ┌─────────────┐   ┌─────────────────┐  │
│  │   api        │   │   ui            │  │
│  │   :8000      │◄──│   :8501         │  │
│  │   FastAPI    │   │   Streamlit     │  │
│  │   2 workers  │   │                 │  │
│  └──────┬───────┘   └─────────────────┘  │
│         │                                │
│    ./data (volume)                       │
│    ./static (volume)                     │
└─────────────────────────────────────────┘
```

단일 Docker 이미지를 빌드하고, `docker-compose.yml`에서 `command`를 달리하여 두 서비스를 실행합니다.

- **api** (포트 8000): FastAPI 백엔드, uvicorn 워커 2개
- **ui** (포트 8501): Streamlit 채팅 UI, api 서비스 헬스체크 통과 후 시작

### 4.2 빌드 및 실행

```bash
# 빌드
docker compose build

# 실행 (백그라운드)
docker compose up -d

# 로그 확인
docker compose logs -f

# 특정 서비스 로그
docker compose logs -f api
docker compose logs -f ui
```

### 4.3 헬스체크

api 서비스에 헬스체크가 설정되어 있습니다:

- 엔드포인트: `GET /api/v1/health`
- 간격: 30초
- 타임아웃: 10초
- 재시도: 3회
- 시작 대기: 30초

ui 서비스는 `depends_on: api (service_healthy)` 조건으로 api가 healthy 상태일 때만 시작됩니다.

### 4.4 초기 데이터 시딩

최초 실행 시 컨테이너 내부에서 시딩 스크립트를 실행합니다.

```bash
docker compose exec api python scripts/seed_structured_data.py
docker compose exec api python scripts/ingest_manuals.py
```

### 4.5 중지 및 정리

```bash
# 중지
docker compose down

# 볼륨 포함 정리 (데이터 삭제됨)
docker compose down -v
```

### 4.6 데이터 지속성

`./data`와 `./static` 디렉토리가 볼륨으로 마운트되어 컨테이너 재시작 시에도 데이터가 유지됩니다.

- `./data/chroma/` — ChromaDB 벡터 데이터
- `./data/inbody.db` — SQLite 구조화 데이터
- `./static/images/` — 매뉴얼 이미지

---

## 5. EC2 배포

### 5.1 인스턴스 요구 사항

| 항목 | 권장 |
|------|------|
| AMI | Amazon Linux 2023 또는 Ubuntu 22.04 |
| 인스턴스 타입 | t3.medium 이상 |
| 스토리지 | 20GB+ (gp3) |
| 보안 그룹 | 인바운드 8000, 8501 포트 |

### 5.2 보안 그룹 설정

| 유형 | 포트 | 소스 | 용도 |
|------|------|------|------|
| HTTP | 8000 | 사내 IP/VPN | FastAPI API |
| HTTP | 8501 | 사내 IP/VPN | Streamlit UI |
| SSH | 22 | 관리자 IP | SSH 접근 |

> 8000, 8501 포트를 전체 공개(0.0.0.0/0)하지 않도록 주의합니다.

### 5.3 UserData를 통한 자동 설정

EC2 인스턴스 생성 시 `deploy/ec2-userdata.sh`를 UserData로 지정하면 자동으로 설정이 완료됩니다.

```bash
aws ec2 run-instances \
  --image-id ami-xxxxxxxxx \
  --instance-type t3.medium \
  --key-name my-keypair \
  --security-group-ids sg-xxxxxxxxx \
  --user-data file://deploy/ec2-userdata.sh \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=inbody-tech-master}]'
```

UserData 스크립트가 수행하는 작업:

1. Docker 및 Docker Compose 설치
2. 프로젝트 Git 클론
3. `docker compose build && docker compose up -d`
4. 초기 데이터 시딩 (최초 1회, 플래그 파일로 중복 방지)

### 5.4 수동 배포

```bash
# EC2 인스턴스에 SSH 접속
ssh -i my-keypair.pem ec2-user@<인스턴스-IP>

# 프로젝트 클론
git clone https://github.com/sammy0329/InBody-Multi-Model-Technical-Support-Agent.git
cd InBody-Multi-Model-Technical-Support-Agent

# .env 파일 생성
cp .env.example .env
vi .env  # API 키 등 설정

# Docker Compose 실행
docker compose build
docker compose up -d
```

### 5.5 업데이트 배포

```bash
cd /home/ec2-user/inbody-app
git pull origin main
docker compose build
docker compose up -d
```

---

## 6. 자동 스케줄러 (CloudFormation)

`deploy/scheduler-cfn.yml`은 EventBridge + Lambda를 사용하여 EC2 인스턴스를 자동으로 시작/중지합니다.

### 6.1 스케줄

| 동작 | 시간 (KST) | cron (UTC) |
|------|------------|------------|
| 시작 | 평일 09:00 | `cron(0 0 ? * MON-FRI *)` |
| 중지 | 평일 19:00 | `cron(0 10 ? * MON-FRI *)` |

> 주말 및 공휴일에는 인스턴스가 중지된 상태로 유지됩니다.

### 6.2 스택 배포

```bash
aws cloudformation create-stack \
  --stack-name inbody-ec2-scheduler \
  --template-body file://deploy/scheduler-cfn.yml \
  --parameters ParameterKey=InstanceId,ParameterValue=i-xxxxxxxxx \
  --capabilities CAPABILITY_NAMED_IAM
```

### 6.3 생성되는 리소스

| 리소스 | 이름 | 설명 |
|--------|------|------|
| IAM Role | `inbody-ec2-scheduler-role` | Lambda 실행 역할 (EC2 start/stop + CloudWatch Logs) |
| Lambda | `inbody-ec2-start` | EC2 시작 함수 |
| Lambda | `inbody-ec2-stop` | EC2 중지 함수 |
| EventBridge Rule | `inbody-ec2-start-schedule` | 평일 09:00 KST 트리거 |
| EventBridge Rule | `inbody-ec2-stop-schedule` | 평일 19:00 KST 트리거 |

### 6.4 스케줄러 비활성화

일시적으로 자동 start/stop을 중지하려면:

```bash
# EventBridge 규칙 비활성화
aws events disable-rule --name inbody-ec2-start-schedule
aws events disable-rule --name inbody-ec2-stop-schedule

# 다시 활성화
aws events enable-rule --name inbody-ec2-start-schedule
aws events enable-rule --name inbody-ec2-stop-schedule
```

### 6.5 스택 삭제

```bash
aws cloudformation delete-stack --stack-name inbody-ec2-scheduler
```

---

## 7. 운영 및 모니터링

### 7.1 서비스 상태 확인

```bash
# Docker 컨테이너 상태
docker compose ps

# API 헬스체크
curl http://localhost:8000/api/v1/health

# 컨테이너 리소스 사용량
docker stats
```

### 7.2 로그 확인

```bash
# 전체 로그
docker compose logs -f

# API 로그만
docker compose logs -f api

# 최근 100줄
docker compose logs --tail=100 api
```

### 7.3 서비스 재시작

```bash
# 전체 재시작
docker compose restart

# 특정 서비스만
docker compose restart api
docker compose restart ui
```

### 7.4 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| ui 서비스 시작 안 됨 | api 헬스체크 실패 | `docker compose logs api`로 에러 확인 |
| API 응답 없음 | `.env` 파일 누락 | `.env` 파일 생성 및 API 키 확인 |
| ChromaDB 에러 | 데이터 디렉토리 권한 | `chmod -R 777 data/` |
| 스케줄러 미작동 | CloudFormation 스택 미배포 | `aws cloudformation describe-stacks` 확인 |
| 컨테이너 OOM | 메모리 부족 | t3.medium 이상 인스턴스 사용 |

### 7.5 포트 구성 요약

| 서비스 | 포트 | 용도 |
|--------|------|------|
| FastAPI | 8000 | REST API + SSE 스트리밍 |
| Streamlit | 8501 | 채팅 UI |
