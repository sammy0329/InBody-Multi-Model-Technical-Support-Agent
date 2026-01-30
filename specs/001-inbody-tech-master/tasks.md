# Tasks: InBody Tech-Master (Multi-Model Edition)

**Input**: 설계 문서: `specs/001-inbody-tech-master/`
**Prerequisites**: plan.md (필수), spec.md (필수), research.md, data-model.md, contracts/

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 실행 가능 (다른 파일, 의존성 없음)
- **[Story]**: 해당 유저 스토리 (US1, US2, US3, US4, US5)
- 모든 태스크에 정확한 파일 경로 포함

---

## Phase 1: 환경 설정 (Setup)

**Purpose**: 프로젝트 초기화 및 기본 구조 생성

- [x] T001 프로젝트 루트에 pyproject.toml 생성 (Python 3.11+, 의존성: fastapi, uvicorn, langchain, langgraph, langchain-openai, chromadb, python-dotenv, pydantic, sqlalchemy, httpx)
- [x] T002 src/ 디렉토리 구조 생성 (models/, graph/nodes/, tools/, rag/, prompts/, api/, db/)
- [x] T003 [P] .env.example 파일 생성 (OPENAI_API_KEY, OPENAI_MODEL, CHROMA_PERSIST_DIR, STRUCTURED_DB_URL, LOG_LEVEL)
- [x] T004 [P] src/config.py에 환경 변수 로드 및 설정 클래스 구현 (pydantic-settings 활용)
- [x] T005 [P] tests/ 디렉토리 구조 생성 (unit/, integration/, contract/) 및 conftest.py 기본 픽스처 작성
- [x] T006 [P] .gitignore 설정 (.env, __pycache__, data/chroma/, *.pyc, .venv/)

---

## Phase 2: 데이터 파이프라인 (Foundational)

**Purpose**: RAG 및 구조화된 데이터 인프라 구축 — 모든 에이전트의 전제 조건

**⚠️ CRITICAL**: 이 페이즈가 완료되어야 모든 User Story 구현이 가능합니다

### 데이터 모델 정의

- [x] T007 src/models/state.py에 AgentState TypedDict 정의 (messages, identified_model, model_tier, intent, retrieved_docs, error_code, support_level, tone_profile, needs_disclaimer, answer, guardrail_passed)
- [x] T008 [P] src/models/inbody_models.py에 InBodyModel 기종 프로필 상수 정의 (270S/580: entry+foldable+casual, 770S/970S: professional+separable+professional)
- [x] T009 [P] src/models/error_codes.py에 ErrorCode Pydantic 모델 및 SQLAlchemy 스키마 정의 (code, model_id, title, description, cause, support_level, resolution_steps, escalation_note)
- [x] T010 [P] src/models/peripherals.py에 PeripheralCompatibility Pydantic 모델 및 SQLAlchemy 스키마 정의 (model_id, peripheral_type, peripheral_name, is_compatible, connection_method, setup_steps)

### 구조화된 DB 설정

- [x] T011 src/db/database.py에 SQLAlchemy 엔진 및 세션 팩토리 구현 (SQLite 개발용, 비동기 지원)
- [x] T012 src/db/schemas.py에 ErrorCode와 PeripheralCompatibility 테이블 정의 (SQLAlchemy ORM)
- [x] T013 data/seed/error_codes.json에 기종별 샘플 에러 코드 데이터 작성 (기종당 최소 5건, Level1/Level3 혼합)
- [x] T014 [P] data/seed/peripheral_compatibility.json에 기종별 샘플 호환표 데이터 작성 (기종당 프린터/PC/바코드 리더기 최소 3건)
- [x] T015 src/db/seed.py에 JSON 시드 데이터를 DB에 로드하는 스크립트 구현
- [x] T016 scripts/seed_structured_data.py에 시드 실행 진입점 구현 (src/db/seed.py 호출)

### RAG 파이프라인 구축

- [x] T017 src/rag/metadata.py에 메타데이터 태깅 유틸리티 구현 (model, category, section_hierarchy, support_level, error_codes 필드 추출)
- [x] T018 src/rag/ingest.py에 PDF 로더 및 청킹 로직 구현 (RecursiveCharacterTextSplitter, 512토큰, 20% 오버랩, 기종별 메타데이터 필수 태깅)
- [x] T018B src/rag/metadata.py에 이미지 메타데이터 필드 추가 (image_url, content_type 파라미터)
- [x] T018C src/tools/manual_search_tool.py 검색 결과 포맷에 image_url 포함 + extract_image_urls() 헬퍼
- [x] T018D src/api/chat.py의 ChatResponse에 image_urls 필드 추가, state/agents에서 image_urls 전달
- [x] T018E src/main.py에 FastAPI StaticFiles 마운트 추가
- [DEFERRED] T018A 이미지 청크 등록 — 자동 추출(PyMuPDF) 방식은 품질 부족으로 제거. 수동 캡처 방식으로 전환 예정 (핵심 매뉴얼 이미지 3~5장을 스크린샷 → static/images/{model}/ 저장 → 등록 스크립트로 Chroma에 이미지 청크 추가). 텍스트 기능 완성 후 진행
- [x] T019 src/rag/vectorstore.py에 Chroma 벡터 DB 초기화 및 기종별 컬렉션 생성 로직 구현 (inbody_270s, inbody_580, inbody_770s, inbody_970s 4개 컬렉션)
- [x] T020 src/rag/vectorstore.py에 기종별 리트리버 팩토리 함수 구현 (model 메타데이터 필터 필수 적용, category 필터는 유지하되 에이전트에서 미사용 — 매뉴얼 PDF가 통합 문서이므로 model 필터만으로 검색)
- [x] T021 scripts/ingest_manuals.py에 PDF 인제스트 실행 스크립트 구현 (data/manuals/{기종}/ 디렉토리 순회, 기종별 컬렉션에 저장)

### 프롬프트 및 톤앤매너

- [x] T022 src/prompts/disclaimers.py에 의학적 면책 문구 상수 정의 ("이 정보는 의학적 진단이 아니며, 전문 의료인의 상담을 대체하지 않습니다.")
- [x] T023 [P] src/prompts/tone_profiles.py에 톤앤매너 프로파일 정의 (casual: 보급형 톤 지시, professional: 전문가용 톤 지시)
- [x] T024 [P] src/prompts/system_prompts.py에 에이전트별 시스템 프롬프트 템플릿 정의 (model_router, intent_router, install, connect, troubleshoot, clinical, guardrail)

### Tool Calling 함수

- [x] T025 src/tools/error_code_tool.py에 lookup_error_code Tool 구현 (model, error_code 파라미터 → DB 조회 → ErrorCode 반환)
- [x] T026 [P] src/tools/error_code_tool.py에 search_errors_by_symptom Tool 구현 (model, symptom_description → 유사 에러 검색)
- [x] T027 [P] src/tools/peripheral_tool.py에 check_peripheral_compatibility Tool 구현 (model, peripheral_type, peripheral_name → 호환 정보 반환)
- [x] T028 src/tools/manual_search_tool.py에 search_manual Tool 구현 (model, query → 기종별 벡터 검색, model 메타데이터 필터 필수. category 파라미터는 선택적으로 유지)

**Checkpoint**: 데이터 파이프라인 준비 완료 — User Story 구현 시작 가능

---

## Phase 3: User Story 1 — 기종 식별 및 라우팅 (Priority: P1) 🎯 MVP

**Goal**: 사용자 입력(텍스트/선택)에서 InBody 기종을 식별하고, 해당 기종 전용 모드로 분기

**Independent Test**: 기종명 입력 시 올바른 기종 식별 + 톤앤매너 적용 확인, 미지원 기종 시 안내 메시지 확인

### LangGraph 기본 골격

- [x] T029 [US1] src/graph/workflow.py에 StateGraph 기본 골격 구현 (AgentState 기반, START → ModelRouter → IntentRouter 기본 엣지)
- [x] T030 [US1] src/graph/edges.py에 ModelRouter 이후 조건부 엣지 구현 (기종 식별 성공 → IntentRouter, 미식별 → 확인 질문, 미지원 → 안내)

### ModelRouter 구현

- [x] T031 [US1] src/graph/nodes/model_router.py에 텍스트 기반 기종 식별 노드 구현 (LLM 호출로 270S/580/770S/970S 분류, model_tier 및 tone_profile 자동 설정)
- [REMOVED] T032 [US1] ~~이미지 기반 기종 식별~~ — 데모 단순화를 위해 제거
- [x] T033 [US1] src/graph/nodes/model_router.py에 기종 미식별 시 확인 질문 생성 로직 구현 (4개 기종 선택지 제시)
- [x] T034 [US1] src/graph/nodes/model_router.py에 미지원 기종 안내 로직 구현 (지원 불가 메시지 + InBody 고객센터 연락처)

### IntentRouter 구현

- [x] T035 [US1] src/graph/nodes/intent_router.py에 의도 분류 노드 구현 (LLM 호출로 install/connect/troubleshoot/clinical/general 분류)
- [x] T036 [US1] src/graph/edges.py에 IntentRouter 이후 조건부 엣지 추가 (intent별 → 각 전문 에이전트 노드로 분기)

### 기본 API 연동

- [x] T037 [US1] src/main.py에 FastAPI 앱 초기화 (CORS, 라우터 등록, 라이프사이클 이벤트로 DB/VectorStore 초기화)
- [x] T038 [US1] src/api/chat.py에 POST /api/v1/chat 엔드포인트 구현 (요청 파싱 → LangGraph workflow invoke → 응답 포매팅)
- [x] T039 [US1] src/api/health.py에 GET /api/v1/health 엔드포인트 구현 (LLM, Vector DB, Structured DB 상태 확인)

**Checkpoint**: 기종 식별 + 의도 분류 + 기본 API가 동작하는 MVP 상태

---

## Phase 4: User Story 2 — 트러블슈팅 에이전트 (Priority: P2)

**Goal**: 에러 코드 분석 및 단계별 해결책 제시, Level 1/Level 3 엄격 구분

**Independent Test**: 에러 코드 입력 시 해당 기종 전용 해결 가이드 제시, Level 3 에러에 서비스 센터 이관 안내 확인

- [x] T040 [US2] src/graph/nodes/troubleshoot_agent.py에 트러블슈팅 에이전트 노드 구현 (에러 코드 추출 → lookup_error_code Tool 호출 → 해결책 생성)
- [x] T041 [US2] src/graph/nodes/troubleshoot_agent.py에 증상 기반 진단 로직 추가 (에러 코드 없이 증상만 입력 시 search_errors_by_symptom 호출 + 매뉴얼 RAG 검색)
- [x] T042 [US2] src/graph/nodes/troubleshoot_agent.py에 Level 1/Level 3 분기 응답 생성 로직 구현 (Level 1: 단계별 해결, Level 3: 서비스 센터 이관 + 경고)
- [x] T043 [US2] src/graph/nodes/troubleshoot_agent.py에 에스컬레이션 로직 추가 (Level 1 해결 실패 시 → 다음 단계 또는 Level 3 이관)
- [x] T044 [US2] src/api/errors.py에 GET /api/v1/models/{model_id}/errors 및 GET /api/v1/models/{model_id}/errors/{error_code} 엔드포인트 구현
- [x] T045 [US2] src/graph/workflow.py에 TroubleshootAgent 노드 및 엣지 등록

**Checkpoint**: 트러블슈팅 흐름이 독립적으로 동작하는 상태

---

## Phase 5: User Story 3 — 설치 도우미 에이전트 (Priority: P3)

**Goal**: 기종별 설치 유형(접이식/분리형)에 맞는 단계별 설치 안내

**Independent Test**: "설치 방법" 문의 시 해당 기종의 조립 유형에 맞는 가이드 정확 제시 확인

- [x] T046 [US3] src/graph/nodes/install_agent.py에 설치 도우미 에이전트 노드 구현 (기종의 installation_type 확인 → search_manual Tool로 설치 매뉴얼 RAG 검색 → 단계별 가이드 생성)
- [x] T047 [US3] src/graph/nodes/install_agent.py에 설치 중 문제 대응 로직 추가 (특정 단계 막힘 시 해당 단계 체크리스트 제시)
- [x] T048 [US3] src/graph/workflow.py에 InstallAgent 노드 및 엣지 등록

**Checkpoint**: 설치 도우미 흐름이 독립적으로 동작하는 상태

---

## Phase 6: User Story 4 — 연동 에이전트 (Priority: P4)

**Goal**: 주변기기 호환 확인 및 연결 절차 안내

**Independent Test**: 주변기기 연결 문의 시 호환표 기반 정확한 호환 여부 + 연결 방법 안내 확인

- [x] T049 [US4] src/graph/nodes/connect_agent.py에 연동 에이전트 노드 구현 (check_peripheral_compatibility Tool 호출 → 호환 여부 확인 → 연결 절차 안내)
- [x] T050 [US4] src/graph/nodes/connect_agent.py에 비호환 주변기기 대응 로직 추가 (비호환 사유 설명 + 대안 추천)
- [x] T051 [US4] src/api/peripherals.py에 GET /api/v1/models/{model_id}/peripherals 및 상세 호환 엔드포인트 구현
- [x] T052 [US4] src/graph/workflow.py에 ConnectAgent 노드 및 엣지 등록

**Checkpoint**: 연동 에이전트 흐름이 독립적으로 동작하는 상태

---

## Phase 7: User Story 5 — 임상 방어 에이전트 (Priority: P5)

**Goal**: 측정 결과 신뢰성 방어 + 생리학적 변수 설명 + 의학적 면책 문구 필수 포함

**Independent Test**: 측정 결과 신뢰성 질문 시 생리학적 설명 + 면책 문구 포함 응답 확인, 진단 요청 시 거절 확인

- [x] T053 [US5] src/graph/nodes/clinical_agent.py에 임상 방어 에이전트 노드 구현 (측정 항목 관련 RAG 검색 → 생리학적 변수 설명 생성 → needs_disclaimer=True 설정)
- [x] T054 [US5] src/graph/nodes/clinical_agent.py에 의학적 진단 요청 감지 및 거절 로직 구현 (질환 관련 질문 → 진단 불가 안내 + 전문 의료인 상담 권고)
- [x] T055 [US5] src/graph/workflow.py에 ClinicalAgent 노드 및 엣지 등록

**Checkpoint**: 임상 방어 흐름이 독립적으로 동작하는 상태

---

## Phase 8: Guardrail 및 통합

**Purpose**: 안전 검증 노드 구현 및 전체 워크플로우 통합

- [ ] T056 src/graph/nodes/guardrail.py에 가드레일 노드 구현:
  - 면책 문구 검증 (needs_disclaimer=True인데 answer에 면책 문구 미포함 시 자동 삽입)
  - 기종 격리 검증 (retrieved_docs의 model 메타데이터와 identified_model 불일치 시 해당 청크 제거)
  - Level 구분 검증 (support_level=Level3인데 사용자 직접 수리 안내가 포함된 경우 차단)
  - 톤앤매너 일관성 확인
- [ ] T057 src/graph/workflow.py에 Guardrail 노드를 모든 에이전트 출력 후에 연결 (Agent → Guardrail → END)
- [ ] T058 src/graph/workflow.py에 Guardrail 미통과 시 응답 수정 → 재검증 루프 구현
- [ ] T059 src/api/chat.py에 POST /api/v1/chat/stream SSE 스트리밍 엔드포인트 구현 (astream_events 활용)
- [ ] T060 src/api/models_api.py에 GET /api/v1/models 및 GET /api/v1/models/{model_id} 엔드포인트 구현
- [ ] T061 src/api/sessions.py에 GET /api/v1/sessions/{thread_id} 및 DELETE /api/v1/sessions/{thread_id} 엔드포인트 구현
- [ ] T062 src/graph/workflow.py에 InMemorySaver 체크포인터 연결 (세션 간 기종 식별 정보 유지)

**Checkpoint**: 모든 에이전트 + 가드레일 + API가 통합된 완전한 시스템

---

## Phase 9: 마무리 및 검증 (Polish)

**Purpose**: 전체 시스템 통합 검증, 엣지 케이스 처리, 품질 개선

- [ ] T063 [P] src/graph/nodes/model_router.py에 대화 중 기종 변경 처리 로직 추가 (기종 재식별 → 이전 기종 기반 응답 폐기)
- [ ] T064 [P] src/graph/edges.py에 기종 비교 질문 감지 로직 추가 ("270S와 580 차이" 같은 질문 시 각 기종 정보 분리 응답)
- [ ] T065 src/rag/vectorstore.py에 RAG 검색 실패 시 폴백 응답 구현 ("현재 정보 검색에 문제가 있습니다" 안내 + 재시도 제안)
- [ ] T066 [P] requirements.txt 또는 pyproject.toml 의존성 목록 최종 확인 및 정리
- [ ] T067 quickstart.md 검증 — 문서 순서대로 클린 환경에서 실행하여 정상 동작 확인

---

## Phase 10: Streamlit 채팅 UI (User Story 6)

**Purpose**: 웹 브라우저에서 사용 가능한 대화형 채팅 인터페이스 구현

**Independent Test**: 브라우저에서 Streamlit UI 접속 → 기종 선택 → 질문 입력 → 스트리밍 응답 확인

- [ ] T068 [US6] ui/api_client.py에 FastAPI 백엔드 HTTP 클라이언트 구현 (POST /chat, POST /chat/stream SSE 수신, GET /health, GET /models)
- [ ] T069 [US6] ui/components.py에 사이드바 컴포넌트 구현 (기종 선택 selectbox, 세션 초기화 버튼, 시스템 상태 표시)
- [ ] T070 [US6] ui/app.py에 Streamlit 메인 채팅 앱 구현 (st.chat_message로 대화 이력 표시, st.chat_input으로 메시지 입력, st.session_state로 thread_id 관리)
- [ ] T071 [US6] ui/app.py에 SSE 스트리밍 응답 연동 구현 (api_client의 stream 함수 → st.write_stream으로 실시간 표시)
- [REMOVED] T072 [US6] ~~이미지 업로드 기종 식별 연동~~ — 데모 단순화를 위해 제거

### 관리자 PDF 문서 관리 페이지

- [ ] T072A [US6] ui/admin.py에 관리자 전용 PDF 관리 페이지 구현 (기종 선택 → 카테고리별 PDF 업로드 UI)
- [ ] T072B [US6] ui/admin.py에 기종별 3종 카테고리 업로드 슬롯 구현 (매뉴얼: 필수, 프린터 호환리스트: 선택, 측정시 주의사항: 선택/공통)
- [ ] T072C [US6] src/api/documents.py에 POST /api/v1/documents/upload 엔드포인트 구현 (PDF 수신 → 저장 → 인제스트 트리거)
- [ ] T072D [US6] src/rag/ingest.py에 업로드된 PDF 실시간 인제스트 함수 추가 (카테고리 메타데이터 태깅 포함)
- [ ] T072E [US6] ui/admin.py에 기종별 업로드 현황 표시 (각 카테고리별 업로드 상태, 문서명, 인제스트 완료 여부)

**Checkpoint**: Streamlit UI에서 전체 채팅 흐름이 동작하고, 관리자 페이지에서 PDF 업로드/관리가 가능한 상태

---

## Phase 11: Docker 및 AWS 배포

**Purpose**: Docker Compose 패키징 및 EC2 Spot 배포, 스케줄 자동 운영

- [ ] T073 Dockerfile 생성 (Python 3.11-slim 베이스, pip install, src/ 및 ui/ 복사)
- [ ] T074 [P] docker-compose.yml 생성 (fastapi-server:8000 + streamlit-ui:8501, 볼륨: data/, 환경변수: .env)
- [ ] T075 [P] deploy/ec2-userdata.sh에 EC2 초기 설정 스크립트 작성 (Docker/Compose 설치, git clone, docker compose up -d)
- [ ] T076 deploy/scheduler-cfn.yml에 EventBridge 스케줄 CloudFormation 템플릿 작성 (평일 09:00 시작, 19:00 종료 KST)
- [ ] T077 docker-compose.yml에 헬스체크 및 자동 재시작 설정 추가 (restart: unless-stopped, healthcheck)

**Checkpoint**: EC2에서 Docker Compose로 전체 시스템이 자동 운영되는 상태

---

## 의존성 및 실행 순서

### Phase 의존성

- **Phase 1 (환경 설정)**: 의존성 없음 — 즉시 시작 가능
- **Phase 2 (데이터 파이프라인)**: Phase 1 완료 필요 — **모든 User Story를 차단**
- **Phase 3 (US1: 기종 식별)**: Phase 2 완료 필요 — LangGraph 기본 골격 포함
- **Phase 4~7 (US2~US5)**: Phase 3 완료 필요 (ModelRouter + IntentRouter + 기본 API 필요)
- **Phase 8 (Guardrail/통합)**: Phase 3~7 중 최소 1개 이상 완료 필요
- **Phase 9 (마무리)**: Phase 8 완료 필요
- **Phase 10 (Streamlit UI)**: Phase 3 완료 필요 (기본 API 엔드포인트 필요) — Phase 4~9와 병렬 가능
- **Phase 11 (배포)**: Phase 10 + Phase 8 완료 필요 — 최종 단계

### User Story 의존성

- **US1 (기종 식별)**: Phase 2 이후 시작 가능 — 다른 스토리에 의존 없음
- **US2 (트러블슈팅)**: US1 완료 필요 (ModelRouter + IntentRouter 필수)
- **US3 (설치 도우미)**: US1 완료 필요 — US2와 독립적으로 병렬 가능
- **US4 (연동)**: US1 완료 필요 — US2, US3와 독립적으로 병렬 가능
- **US5 (임상 방어)**: US1 완료 필요 — US2, US3, US4와 독립적으로 병렬 가능

### 병렬 실행 기회

```bash
# Phase 2 내 병렬 가능한 그룹:
Task: T008 (기종 프로필) | T009 (에러코드 모델) | T010 (주변기기 모델)
Task: T013 (에러 시드 데이터) | T014 (호환표 시드 데이터)
Task: T022 (면책 문구) | T023 (톤앤매너) | T024 (시스템 프롬프트)
Task: T025-T026 (에러 Tool) | T027 (주변기기 Tool)

# Phase 3 완료 후 US2~US5 병렬 가능:
Developer A: Phase 4 (US2 트러블슈팅)
Developer B: Phase 5 (US3 설치 도우미)
Developer C: Phase 6 (US4 연동)
Developer D: Phase 7 (US5 임상 방어)
```

---

## 구현 전략

### MVP First (User Story 1만)

1. Phase 1 완료: 환경 설정
2. Phase 2 완료: 데이터 파이프라인 (⚠️ 핵심 — 가장 시간 소요)
3. Phase 3 완료: 기종 식별 + 의도 분류 + 기본 API
4. **STOP AND VALIDATE**: 기종 식별이 정확하게 동작하는지 확인
5. 데모 가능 상태

### 점진적 확장

1. 환경 설정 + 데이터 파이프라인 → 기반 완성
2. US1 (기종 식별) → 테스트 → 데모 **(MVP!)**
3. US2 (트러블슈팅) → 테스트 → 데모 (가장 빈번한 지원 유형)
4. US3 (설치 도우미) → 테스트 → 데모
5. US4 (연동) → 테스트 → 데모
6. US5 (임상 방어) → 테스트 → 데모
7. Guardrail 통합 + 마무리 → 최종 검증
8. Streamlit UI → 전체 채팅 흐름 연동
9. Docker + EC2 배포 → 데모 서버 운영 (평일 09:00~19:00 KST)

---

## Notes

- [P] 태스크 = 다른 파일, 의존성 없음
- [Story] 라벨은 spec.md의 유저 스토리에 매핑
- 각 User Story는 독립적으로 완성 및 테스트 가능
- 체크포인트에서 해당 스토리 독립 검증 수행
- 논리적 그룹 단위로 커밋
- 기종 격리 원칙 위반 여부는 모든 단계에서 검증
