# 빠른 시작 가이드: InBody Tech-Master

**Branch**: `001-inbody-tech-master`
**Date**: 2026-01-30

## 사전 요구사항

- Python 3.11 이상
- OpenAI API 키
- Git

## 1. 프로젝트 설정

```bash
# 저장소 클론
git clone <repository-url>
cd InBody-Multi-Model-Technical-Support-Agent

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

## 2. 환경 변수 설정

`.env` 파일을 프로젝트 루트에 생성한다:

```env
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o
OPENAI_MINI_MODEL=gpt-4o-mini
CHROMA_PERSIST_DIR=./data/chroma
STRUCTURED_DB_URL=sqlite:///./data/inbody.db
LOG_LEVEL=INFO
```

## 3. 데이터 준비

```bash
# 데이터 디렉토리 생성
mkdir -p data/manuals data/chroma

# PDF 매뉴얼 배치 (기종별 디렉토리)
# data/manuals/270S/*.pdf
# data/manuals/580/*.pdf
# data/manuals/770S/*.pdf
# data/manuals/970S/*.pdf

# 구조화된 데이터(에러 코드, 호환표) 시딩
python scripts/seed_structured_data.py

# PDF 매뉴얼 인제스트 (청킹 + 임베딩 + 벡터 DB 저장)
python scripts/ingest_manuals.py
```

## 4. 서버 실행

```bash
# 개발 서버 시작
uvicorn src.main:app --reload --port 8000

# 서버 상태 확인
curl http://localhost:8000/api/v1/health
```

## 5. 테스트

```bash
# 전체 테스트 실행
pytest

# 특정 테스트 실행
pytest tests/unit/test_model_router.py -v
pytest tests/integration/test_chat_flow.py -v
```

## 6. 기본 사용법

### 채팅 요청

```bash
# 기종 식별
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "InBody 770S를 사용하고 있어요", "thread_id": "session-001"}'

# 트러블슈팅
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "에러코드 E003이 떠요", "thread_id": "session-001"}'
```

### 에러 코드 직접 조회

```bash
curl http://localhost:8000/api/v1/models/770S/errors/E003
```

### 주변기기 호환 확인

```bash
curl http://localhost:8000/api/v1/models/580/peripherals?type=printer
```

## 검증 체크리스트

- [ ] `/api/v1/health` 응답이 모든 컴포넌트 "ok" 반환
- [ ] "270S"를 입력하면 보급형 모드(casual 톤)로 응답
- [ ] "970S"를 입력하면 전문가용 모드(professional 톤)로 응답
- [ ] 기종 미식별 상태에서 기술 질문 시 기종 확인 질문 발생
- [ ] 에러 코드 조회 시 해당 기종 전용 정보만 반환
- [ ] 임상 관련 응답에 면책 문구 포함
- [ ] Level 3 조치에 대해 서비스 센터 이관 안내
