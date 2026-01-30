# 데이터 모델: InBody Tech-Master

**Branch**: `001-inbody-tech-master`
**Date**: 2026-01-30

## 1. AgentState (LangGraph 워크플로우 상태)

워크플로우 전체에서 공유되는 중앙 상태 객체이다.

```
AgentState
├── messages: 대화 메시지 이력 (add_messages 리듀서로 자동 관리)
├── identified_model: 식별된 기종 (270S | 580 | 770S | 970S | null)
├── model_tier: 기종 분류 (entry | professional | null)
├── intent: 사용자 의도 (install | connect | troubleshoot | clinical | general | null)
├── retrieved_docs: RAG 검색 결과 문서 목록
├── error_code: 감지된 에러 코드 (있을 경우)
├── support_level: 판별된 지원 수준 (Level1 | Level3 | null)
├── tone_profile: 적용할 톤앤매너 (casual | professional)
├── needs_disclaimer: 의학적 면책 문구 필요 여부 (boolean)
├── answer: 생성된 최종 답변
└── guardrail_passed: 가드레일 통과 여부 (boolean)
```

**필드 상세**:

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| messages | Sequence[BaseMessage] | [] | 대화 이력. add_messages 리듀서로 추가 전용 |
| identified_model | str \| None | None | 식별된 기종명. ModelRouter가 설정 |
| model_tier | str \| None | None | "entry"(270S/580) 또는 "professional"(770S/970S) |
| intent | str \| None | None | IntentRouter가 분류한 사용자 의도 |
| retrieved_docs | list[Document] | [] | RAG 검색 또는 Tool Calling 결과 문서 |
| error_code | str \| None | None | 사용자 입력에서 추출된 에러 코드 |
| support_level | str \| None | None | 트러블슈팅 시 판별된 지원 수준 |
| tone_profile | str | "casual" | 응답 톤앤매너. model_tier에 의해 결정 |
| needs_disclaimer | bool | False | 임상 관련 응답 시 True로 설정 |
| answer | str | "" | 최종 생성된 답변 텍스트 |
| guardrail_passed | bool | False | 가드레일 노드 통과 여부 |

**상태 전이 규칙**:
- `identified_model`이 None이면 ModelRouter로 분기
- `identified_model` 설정 시 `model_tier`와 `tone_profile` 자동 결정
- `intent`가 "clinical"이면 `needs_disclaimer`를 True로 설정
- `guardrail_passed`가 False이면 답변 재생성 또는 차단

## 2. InBodyModel (기종 정보)

지원되는 InBody 기종의 프로필 정보이다.

```
InBodyModel
├── model_id: 기종 식별자 (270S, 580, 770S, 970S)
├── display_name: 표시 이름 (예: "InBody 270S")
├── tier: 분류 (entry | professional)
├── installation_type: 설치 유형 (foldable | separable)
├── tone_profile: 톤앤매너 (casual | professional)
├── measurement_items: 측정 항목 목록
└── supported_peripherals: 지원 주변기기 유형 목록
```

**인스턴스 데이터**:

| model_id | tier | installation_type | tone_profile |
|----------|------|-------------------|--------------|
| 270S | entry | foldable | casual |
| 580 | entry | foldable | casual |
| 770S | professional | separable | professional |
| 970S | professional | separable | professional |

## 3. ErrorCode (에러 코드)

기종별 에러 코드 정보를 저장하는 구조화된 데이터이다. Tool Calling으로 조회한다.

```
ErrorCode
├── code: 에러 코드 (예: "E003")
├── model_id: 대상 기종 (FK → InBodyModel)
├── title: 에러 제목
├── description: 에러 상세 설명
├── cause: 원인 설명
├── support_level: 지원 수준 (Level1 | Level3)
├── resolution_steps: 해결 단계 목록 (순서 있음)
└── escalation_note: Level3 이관 시 안내 메시지 (Level3인 경우만)
```

**유효성 규칙**:
- `code`와 `model_id` 조합은 유일해야 한다
- 동일한 에러 코드가 기종마다 다른 해결 절차를 가질 수 있다
- `support_level`이 "Level3"이면 `escalation_note`는 반드시 존재해야 한다
- `resolution_steps`는 최소 1개 이상이어야 한다

## 4. PeripheralCompatibility (주변기기 호환표)

기종별 주변기기 호환 정보를 저장하는 구조화된 데이터이다. Tool Calling으로 조회한다.

```
PeripheralCompatibility
├── model_id: 대상 기종 (FK → InBodyModel)
├── peripheral_type: 주변기기 유형 (printer | pc_software | barcode_reader | etc)
├── peripheral_name: 주변기기 이름/모델명
├── is_compatible: 호환 여부 (boolean)
├── connection_method: 연결 방식 (USB, Bluetooth, Wi-Fi, Serial 등)
├── driver_version: 필요한 드라이버 버전 (해당 시)
├── setup_steps: 설정 절차 (순서 있음)
└── notes: 추가 참고사항
```

**유효성 규칙**:
- `model_id`, `peripheral_type`, `peripheral_name` 조합은 유일해야 한다
- `is_compatible`이 True이면 `connection_method`와 `setup_steps`는 반드시 존재해야 한다
- `is_compatible`이 False이면 `notes`에 비호환 사유를 포함해야 한다

## 5. ManualChunk (매뉴얼 문서 청크)

PDF 매뉴얼에서 추출된 벡터 검색 대상 텍스트 청크이다.

```
ManualChunk
├── chunk_id: 청크 고유 식별자
├── content: 청크 텍스트 내용
├── embedding: 벡터 임베딩 (1536차원, OpenAI text-embedding-3-small)
└── metadata:
    ├── model: 기종명 (270S | 580 | 770S | 970S)
    ├── category: 분류 (installation | connectivity | troubleshooting | clinical)
    ├── section_hierarchy: 매뉴얼 목차 경로 (예: "3 > 3.2 > 3.2.1")
    ├── parent_section: 상위 섹션 제목
    ├── support_level: 지원 수준 (Level1 | Level3) — troubleshooting만
    ├── error_codes: 관련 에러 코드 배열 — troubleshooting만
    └── source_page: 원본 PDF 페이지 번호
```

**유효성 규칙**:
- `metadata.model`은 반드시 존재해야 한다 (기종 격리 보장)
- `metadata.category`는 반드시 존재해야 한다
- 한 청크는 반드시 하나의 기종에만 속해야 한다

## 6. ConversationSession (대화 세션)

사용자와의 대화 세션 상태를 추적한다. LangGraph 체크포인터로 관리된다.

```
ConversationSession
├── thread_id: 세션 고유 식별자
├── identified_model: 현재 식별된 기종
├── model_tier: 기종 분류
├── created_at: 세션 생성 시각
├── last_active_at: 마지막 활동 시각
└── message_count: 총 메시지 수
```

## 엔티티 관계

```
ConversationSession  1 --- 1  AgentState (체크포인터로 연결)
InBodyModel          1 --- *  ErrorCode
InBodyModel          1 --- *  PeripheralCompatibility
InBodyModel          1 --- *  ManualChunk (metadata.model로 연결)
AgentState           * --- *  ManualChunk (retrieved_docs로 참조)
```

## 저장소 매핑

| 엔티티 | 저장소 | 접근 방식 |
|--------|--------|-----------|
| AgentState | LangGraph 체크포인터 (InMemory / PostgreSQL) | 워크플로우 자동 관리 |
| InBodyModel | Python 설정 파일 (상수) | 직접 참조 |
| ErrorCode | SQLite (개발) / PostgreSQL (프로덕션) | Tool Calling |
| PeripheralCompatibility | SQLite (개발) / PostgreSQL (프로덕션) | Tool Calling |
| ManualChunk | Chroma (개발) / Pinecone (프로덕션) | RAG 벡터 검색 |
| ConversationSession | LangGraph 체크포인터 | thread_id 기반 관리 |
