# 기술 조사 보고서: InBody Tech-Master

**Branch**: `001-inbody-tech-master`
**Date**: 2026-01-30

## 1. LLM 프로바이더 선택

- **Decision**: OpenAI GPT-4o (메인), GPT-4o-mini (가드레일/경량 작업)
- **Rationale**: LangChain/LangGraph와의 통합 성숙도가 가장 높고, Vision 기능(이미지 기반 기종 식별)을 기본 지원한다. Tool Calling API가 안정적이며, 한국어 성능이 검증되어 있다.
- **Alternatives considered**:
  - Anthropic Claude: 한국어 성능 우수하나 LangGraph 통합 사례가 상대적으로 적음
  - Google Gemini: Vision 성능은 우수하나 Tool Calling 안정성이 OpenAI 대비 낮음

## 2. Vector DB 선택

- **Decision**: 개발 환경은 Chroma(컬렉션 기반 격리), 프로덕션은 Pinecone(네임스페이스 기반 격리)
- **Rationale**:
  - Chroma: 로컬 개발 시 인프라 비용 0원, `PersistentClient`로 프로토타이핑에 적합
  - Pinecone: 물리적 네임스페이스 격리로 SC-005(기종 간 정보 오염 0%) 보장. 하이브리드 검색(벡터 + 키워드)으로 에러 코드 정확 매칭 지원
- **Alternatives considered**:
  - Weaviate: 멀티 테넌시 지원 우수하나 self-hosted 운영 부담
  - pgvector: PostgreSQL 기반으로 익숙하나 메타데이터 필터링 성능이 전용 Vector DB 대비 부족

## 3. 기종 격리 전략

- **Decision**: 물리적 격리(컬렉션/네임스페이스 분리) + 논리적 격리(메타데이터 필터) 이중 방어
- **Rationale**: 헌법 원칙 II(엄격한 기종 격리) 준수를 위해 단일 방어선만으로는 불충분. 물리적 분리로 1차 차단 후, 메타데이터 필터로 2차 검증하며, 검색 결과에 대한 후처리 검증(3차)을 추가한다.
- **Alternatives considered**:
  - 메타데이터 필터 단독: 필터 누락 시 오염 위험 존재
  - 완전 독립 인스턴스: 비용 과다, 유지보수 복잡

## 4. 문서 청킹 전략

- **Decision**: 재귀적 분할(Recursive), 512 토큰, 20% 오버랩, 계층적 메타데이터 태깅
- **Rationale**: InBody 매뉴얼은 팩토이드 쿼리(에러 코드, 호환성 확인)가 주 사용 패턴이므로 512 토큰이 최적. 기술 문서의 TechQA 벤치마크에서 512 토큰이 61.3% recall@1 달성. 오버랩 20%로 문맥 손실 방지.
- **필수 메타데이터 필드**:
  - `model`: 기종명 (270S, 580, 770S, 970S)
  - `category`: 분류 (installation, connectivity, troubleshooting, clinical)
  - `section_hierarchy`: 매뉴얼 목차 경로
  - `support_level`: 지원 수준 (Level1, Level3) — 트러블슈팅 문서 한정
  - `error_codes`: 관련 에러 코드 배열 — 트러블슈팅 문서 한정
- **Alternatives considered**:
  - 1024 토큰: 분석적 쿼리에 유리하나 팩토이드 쿼리 정밀도 저하
  - 시맨틱 청킹: 비용 높고 기술 문서에서의 이점이 재귀적 분할 대비 미미

## 5. 구조화된 데이터 접근 방식

- **Decision**: 에러 코드 테이블과 호환표는 Tool Calling, 매뉴얼 본문은 RAG 벡터 검색
- **Rationale**: 에러 코드(예: "E003")와 호환 주변기기는 정확한 매칭이 필요한 구조화된 데이터로, 벡터 유사도 검색보다 Tool Calling을 통한 직접 DB 조회가 정확도와 일관성이 높다. 반면 설치 절차, 증상 기반 진단, 임상 방어 설명은 비정형 텍스트로 벡터 검색이 적합하다.
- **Alternatives considered**:
  - 모든 데이터 RAG 검색: 구조화된 데이터에서 할루시네이션 위험
  - 모든 데이터 Tool Calling: 비정형 텍스트 대응 불가

## 6. LangGraph 워크플로우 아키텍처

- **Decision**: 커스텀 그래프 기반 라우팅 (Supervisor 패턴 변형)
- **Rationale**: ModelRouter → IntentRouter → 전문 에이전트 체인은 고정된 라우팅 경로를 가지므로, 범용 Supervisor보다 커스텀 conditional edges가 더 예측 가능하고 디버깅이 용이하다. 가드레일 노드를 출력 직전에 배치하여 모든 응답에 대한 안전 검증을 보장한다.
- **Alternatives considered**:
  - langgraph-supervisor 라이브러리: 범용적이나 라우팅 경로가 고정된 본 프로젝트에서는 불필요한 추상화
  - 계층적 멀티 에이전트: 에이전트가 4개로 제한적이므로 단일 계층으로 충분

## 7. 상태 관리 설계

- **Decision**: TypedDict 기반 AgentState, add_messages 리듀서 사용
- **Rationale**: LangGraph v0.2+에서 TypedDict가 필수이며, `Annotated[Sequence[BaseMessage], add_messages]` 패턴으로 대화 이력을 자동 관리한다. 기종 식별 결과, 의도, 검색 문서 등 커스텀 필드를 추가하여 전체 워크플로우 상태를 추적한다.
- **Alternatives considered**:
  - Pydantic BaseModel: LangGraph v0.2+에서 미지원
  - 딕셔너리 직접 관리: 타입 안전성 부재, 런타임 에러 위험

## 8. 대화 지속성 및 세션 관리

- **Decision**: 개발 환경은 InMemorySaver, 프로덕션은 PostgresSaver
- **Rationale**: LangGraph의 체크포인터를 활용하여 세션 간 대화 상태를 유지한다. 기종 식별 결과가 세션 전체에 걸쳐 유지되어야 하므로(엣지 케이스 요구사항), 체크포인터 기반 상태 지속성이 필수이다.
- **Alternatives considered**:
  - Redis 기반 커스텀 세션: LangGraph 체크포인터 대비 추가 개발 비용
  - 클라이언트 측 상태 관리: 기종 정보가 클라이언트에 노출되어 변조 위험

## 9. 톤앤매너 적용 전략

- **Decision**: 시스템 프롬프트 동적 주입 방식
- **Rationale**: 기종 식별 후 보급형/전문가용 분류에 따라 시스템 프롬프트를 동적으로 교체한다. 프롬프트 템플릿에 톤앤매너 지시를 포함하여 일관성을 보장한다.
- **프롬프트 매핑**:
  - 보급형 (270S/580): "친근하고 실용적인 톤으로 답변하세요. 전문 용어는 쉬운 설명과 함께 사용하세요."
  - 전문가용 (770S/970S): "전문적이고 근거 중심적인 톤으로 답변하세요. 기술 용어와 통계적 맥락을 포함하세요."

## 10. 테스팅 전략

- **Decision**: pytest + pytest-asyncio (단위/통합), httpx (API 계약)
- **Rationale**: FastAPI의 비동기 특성에 맞는 pytest-asyncio 사용. httpx의 AsyncClient로 API 엔드포인트 계약 테스트 수행. LangGraph 노드 단위 테스트는 모의 상태 주입으로 격리 테스트 가능.
- **Alternatives considered**:
  - unittest: 비동기 테스트 지원 미흡
  - Robot Framework: 오버스펙, 학습 곡선 높음
