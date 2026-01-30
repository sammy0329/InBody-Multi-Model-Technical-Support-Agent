# 구현 계획서: InBody Tech-Master (Multi-Model Edition)

**Branch**: `001-inbody-tech-master` | **Date**: 2026-01-30 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/001-inbody-tech-master/spec.md`

## 요약

InBody 기종(270S, 580, 770S, 970S) 식별 기반 멀티 에이전트 기술 지원 시스템을 구축한다. Python(FastAPI) + LangGraph 아키텍처로, ModelRouter → IntentRouter → 4개 전문 에이전트(Install, Connect, Troubleshoot, Clinical) → Guardrail 워크플로우를 구현한다. 기종별 PDF 매뉴얼은 RAG로, 에러코드/호환표는 Tool Calling으로 참조하며, 기종 간 정보 격리와 의학적 면책 문구를 보장한다. Streamlit 채팅 UI를 통해 사용자 인터페이스를 제공하며, AWS EC2 Spot 인스턴스에 Docker Compose로 배포한다.

## 기술 컨텍스트

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI, LangChain, LangGraph, OpenAI API (GPT-4o / GPT-4o-mini), Streamlit
**Storage**: Chroma (개발) / Pinecone (프로덕션) — 벡터 DB, SQLite (개발) / PostgreSQL (프로덕션) — 구조화 DB
**Testing**: pytest, pytest-asyncio, httpx
**Target Platform**: AWS EC2 Spot (t3.small) — Docker Compose
**Project Type**: Single project (API 서버 + Streamlit UI)
**Performance Goals**: 응답 시간 p95 < 5초 (LLM 호출 포함), 동시 세션 100개 이상
**Constraints**: 기종 간 정보 오염 0%, 임상 면책 문구 100% 포함, 한국어 전용
**Scale/Scope**: 4개 기종, 4개 전문 에이전트, 기종당 매뉴얼 1~3건

## 헌법 검증 (Constitution Check)

*GATE: Phase 0 진행 전 반드시 통과해야 한다. Phase 1 설계 완료 후 재검증한다.*

| 원칙 | 게이트 조건 | 상태 |
|------|-------------|------|
| I. 언어 규칙 | 모든 코드 주석, 커밋, 문서가 한국어로 작성되는가? | ✅ 통과 — 프롬프트 템플릿 및 응답 모두 한국어로 설계 |
| II. 엄격한 기종 격리 | RAG 검색 시 기종 메타데이터 필터가 적용되는가? 기종 간 정보 혼합 방지 구조가 있는가? | ✅ 통과 — 물리적 격리(컬렉션/네임스페이스 분리) + 논리적 격리(메타데이터 필터) + 후처리 검증 3중 방어 |
| III. 안전 및 면책 | 임상 응답에 면책 문구가 자동 포함되는가? Level 1/3 구분이 구현되는가? | ✅ 통과 — Guardrail 노드에서 needs_disclaimer 확인, ErrorCode 엔티티에 support_level 필드 포함 |
| IV. 톤앤매너 | 보급형/전문가용 톤 분기가 설계되어 있는가? | ✅ 통과 — model_tier 기반 시스템 프롬프트 동적 주입 |
| V. UI 및 배포 | Streamlit 네이티브 기능 우선 사용, EC2 Spot + Docker Compose 배포인가? | ✅ 통과 — st.chat_message/st.sidebar 활용, EC2 Spot(t3.small) + EventBridge 스케줄 설계 |
| VI. 오류 수정 및 진척도 | tasks.md 체크박스 관리 및 에러 즉시 수정 절차가 있는가? | ✅ 통과 — 태스크 완료 시 [x] 업데이트 원칙 수립 |
| VII. 사용자 의사결정 존중 | 주요 설계 결정 시 사용자 승인 절차가 있는가? | ✅ 통과 — AskUserQuestion을 통한 옵션 제시 및 승인 |

## 프로젝트 구조

### 문서 (이 기능)

```text
specs/001-inbody-tech-master/
├── spec.md              # 기능 명세서
├── plan.md              # 이 파일 (구현 계획서)
├── research.md          # Phase 0 기술 조사 보고서
├── data-model.md        # Phase 1 데이터 모델 설계
├── quickstart.md        # Phase 1 빠른 시작 가이드
├── contracts/
│   └── api-contract.md  # Phase 1 API 계약
├── checklists/
│   └── requirements.md  # 명세서 품질 체크리스트
└── tasks.md             # Phase 2 태스크 목록 (/speckit.tasks 생성)
```

### 소스 코드 (저장소 루트)

```text
src/
├── main.py                      # FastAPI 앱 진입점, 라우터 등록
├── config.py                    # 환경 변수 및 설정 관리
├── models/
│   ├── state.py                 # AgentState TypedDict 정의
│   ├── inbody_models.py         # InBodyModel 기종 프로필 (상수)
│   ├── error_codes.py           # ErrorCode 데이터 모델
│   └── peripherals.py           # PeripheralCompatibility 데이터 모델
├── graph/
│   ├── workflow.py              # LangGraph 워크플로우 정의 (메인 그래프)
│   ├── nodes/
│   │   ├── model_router.py      # 기종 식별 노드
│   │   ├── intent_router.py     # 의도 분류 노드
│   │   ├── install_agent.py     # 설치 도우미 에이전트 노드
│   │   ├── connect_agent.py     # 연동 에이전트 노드
│   │   ├── troubleshoot_agent.py # 트러블슈팅 에이전트 노드
│   │   ├── clinical_agent.py    # 임상 방어 에이전트 노드
│   │   └── guardrail.py         # 가드레일 (안전 검증) 노드
│   └── edges.py                 # 조건부 엣지 라우팅 함수
├── tools/
│   ├── error_code_tool.py       # 에러 코드 조회 Tool
│   ├── peripheral_tool.py       # 주변기기 호환 조회 Tool
│   └── manual_search_tool.py    # 매뉴얼 RAG 검색 Tool
├── rag/
│   ├── vectorstore.py           # Vector DB 초기화 및 리트리버 팩토리
│   ├── ingest.py                # PDF 매뉴얼 인제스트 (청킹 + 임베딩)
│   └── metadata.py              # 메타데이터 태깅 및 필터 유틸리티
├── prompts/
│   ├── system_prompts.py        # 에이전트별 시스템 프롬프트 템플릿
│   ├── tone_profiles.py         # 톤앤매너 프로파일 (casual / professional)
│   └── disclaimers.py           # 면책 문구 상수
├── api/
│   ├── chat.py                  # 채팅 엔드포인트 (POST /chat, /chat/stream)
│   ├── errors.py                # 에러 코드 엔드포인트
│   ├── peripherals.py           # 주변기기 엔드포인트
│   ├── models_api.py            # 기종 정보 엔드포인트
│   ├── sessions.py              # 세션 관리 엔드포인트
│   └── health.py                # 헬스 체크 엔드포인트
└── db/
    ├── database.py              # DB 연결 및 세션 관리
    ├── seed.py                  # 초기 데이터 시딩 (에러 코드, 호환표)
    └── schemas.py               # SQLAlchemy / Pydantic 스키마

ui/
├── app.py                       # Streamlit 메인 앱 (채팅 인터페이스)
├── components.py                # UI 컴포넌트 (사이드바, 기종 선택 등)
└── api_client.py                # FastAPI 백엔드 HTTP 클라이언트

scripts/
├── seed_structured_data.py      # 구조화된 데이터 시딩 스크립트
└── ingest_manuals.py            # PDF 매뉴얼 인제스트 스크립트

data/
├── manuals/                     # PDF 매뉴얼 원본 (기종별 하위 디렉토리)
│   ├── 270S/
│   ├── 580/
│   ├── 770S/
│   └── 970S/
├── seed/                        # 시드 데이터 (JSON/CSV)
│   ├── error_codes.json
│   └── peripheral_compatibility.json
└── chroma/                      # Chroma 영속 저장소 (개발용)

tests/
├── conftest.py                  # 테스트 픽스처 (DB, 클라이언트, 모의 LLM)
├── unit/
│   ├── test_model_router.py     # 기종 식별 단위 테스트
│   ├── test_intent_router.py    # 의도 분류 단위 테스트
│   ├── test_guardrail.py        # 가드레일 단위 테스트
│   ├── test_tone_profiles.py    # 톤앤매너 적용 테스트
│   └── test_metadata_filter.py  # 메타데이터 필터 격리 테스트
├── integration/
│   ├── test_chat_flow.py        # 전체 채팅 흐름 통합 테스트
│   ├── test_troubleshoot_flow.py # 트러블슈팅 흐름 테스트
│   └── test_model_isolation.py  # 기종 격리 통합 테스트
└── contract/
    ├── test_chat_api.py         # 채팅 API 계약 테스트
    ├── test_error_api.py        # 에러 코드 API 계약 테스트
    └── test_peripheral_api.py   # 주변기기 API 계약 테스트
```

**구조 결정**: 단일 프로젝트(Single project) 구조를 선택한다. FastAPI 백엔드 + Streamlit 프론트엔드를 하나의 저장소에서 관리하며, LangGraph 워크플로우를 중심으로 `graph/`, `tools/`, `rag/`, `prompts/` 디렉토리로 관심사를 분리한다. `ui/` 디렉토리에서 Streamlit 채팅 UI를 독립 실행한다.

## LangGraph 워크플로우 설계

```text
START
  │
  ▼
[ModelRouter] ──── 기종 식별 (텍스트/선택)
  │
  ├── 기종 미식별 → 기종 확인 질문 → END
  ├── 미지원 기종 → 지원 불가 안내 → END
  │
  ▼
[IntentRouter] ──── 의도 분류
  │
  ├── install      → [InstallAgent]
  ├── connect      → [ConnectAgent]
  ├── troubleshoot → [TroubleshootAgent]
  ├── clinical     → [ClinicalAgent]
  └── general      → [일반 응답 생성]
                          │
                          ▼
                    [Guardrail] ──── 안전 검증
                          │
                          ├── 통과   → END (응답 반환)
                          └── 미통과 → 응답 수정 후 재검증
```

**각 에이전트 내부 체인**:
1. Context 추출 (상태에서 기종/의도/이전 대화 추출)
2. 검색 쿼리 생성 (RAG 검색 또는 Tool Calling)
3. 답변 생성 (톤앤매너 적용된 프롬프트로 LLM 호출)
4. 가드레일 전달 (면책 문구, 기종 격리, Level 구분 검증)

## 기종 격리 아키텍처 (3중 방어)

```text
Layer 1: 물리적 격리
├── Chroma: 기종별 별도 컬렉션 (inbody_270s, inbody_580, ...)
└── Pinecone: 기종별 별도 네임스페이스 (model-270s, model-580, ...)

Layer 2: 논리적 격리
└── 모든 RAG 검색에 metadata.model 필터 필수 적용

Layer 3: 후처리 검증
└── Guardrail 노드에서 검색 결과의 model 메타데이터와
    현재 identified_model 일치 여부 확인, 불일치 시 해당 청크 제거
```

## Streamlit 프론트엔드 설계

```text
┌─────────────────────────────────────────┐
│              Streamlit App              │
│  ┌─────────────┐  ┌──────────────────┐  │
│  │   Sidebar    │  │   Chat Area      │  │
│  │             │  │                  │  │
│  │ 기종 선택    │  │ st.chat_message  │  │
│  │ 세션 관리    │  │ (대화 이력)       │  │
│  │ 시스템 상태  │  │                  │  │
│  │             │  │ st.chat_input    │  │
│  │             │  │ (메시지 입력)     │  │
│  └─────────────┘  └──────────────────┘  │
│                                         │
│  api_client.py → FastAPI (port 8000)    │
└─────────────────────────────────────────┘
```

**주요 기능**:
- `st.chat_message`/`st.chat_input`으로 대화형 채팅 UI
- 사이드바: 기종 직접 선택, 세션 초기화
- `st.write_stream`으로 SSE 스트리밍 응답 실시간 표시
- 세션 상태(`st.session_state`)로 thread_id 관리

## 배포 아키텍처 (AWS EC2 Spot)

```text
AWS EC2 Spot (t3.small, ap-northeast-2)
├── Docker Compose
│   ├── fastapi-server (port 8000)
│   │   └── uvicorn src.main:app
│   └── streamlit-ui (port 8501)
│       └── streamlit run ui/app.py
├── EBS (gp3, 20GB)
│   ├── data/chroma/       # 벡터 DB 영속 저장소
│   └── data/inbody.db     # SQLite 구조화 DB
├── Security Group
│   ├── 8501/tcp (Streamlit UI — 외부 접근)
│   └── 8000/tcp (FastAPI — 내부 또는 선택적 외부)
├── Elastic IP (고정 접속 주소)
└── EventBridge + Lambda (자동 스케줄링)
    ├── cron(0 0 * * MON-FRI) → ec2:StartInstances  # 09:00 KST
    └── cron(0 10 * * MON-FRI) → ec2:StopInstances  # 19:00 KST
```

**비용 (월 예상)**: ~$5 (EC2 Spot ~$1.3 + EBS ~$2.3 + EIP ~$1.5)

**배포 파일**:
- `Dockerfile` — Python 앱 이미지 (FastAPI + Streamlit 공통 베이스)
- `docker-compose.yml` — 멀티 서비스 구성
- `deploy/ec2-userdata.sh` — EC2 초기 설정 스크립트
- `deploy/scheduler.tf` 또는 `deploy/scheduler-cfn.yml` — EventBridge 스케줄 IaC

## Complexity Tracking

> 헌법 검증 위반 없음. 기록 불필요.

해당 없음.
