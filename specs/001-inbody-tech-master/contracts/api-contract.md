# API 계약: InBody Tech-Master

**Branch**: `001-inbody-tech-master`
**Date**: 2026-01-30
**Base URL**: `/api/v1`

## 1. 채팅 엔드포인트

### POST /api/v1/chat

사용자 메시지를 받아 AI 에이전트 응답을 반환한다.

**요청**:

```
{
  "message": string (필수) — 사용자 입력 텍스트,
  "thread_id": string (필수) — 대화 세션 식별자
}
```

**응답 (200)**:

```
{
  "response": string — AI 에이전트 응답 텍스트,
  "identified_model": string | null — 식별된 기종 (270S, 580, 770S, 970S),
  "intent": string | null — 분류된 의도 (install, connect, troubleshoot, clinical),
  "support_level": string | null — 지원 수준 (Level1, Level3),
  "disclaimer_included": boolean — 면책 문구 포함 여부,
  "sources": [
    {
      "title": string — 참조 문서 제목,
      "section": string — 참조 섹션,
      "page": number | null — 원본 PDF 페이지
    }
  ]
}
```

**오류 응답**:

| 코드 | 조건 | 본문 |
|------|------|------|
| 400 | message가 비어있거나 thread_id 누락 | `{"error": "message와 thread_id는 필수입니다"}` |
| 422 | 요청 형식 오류 | `{"error": "요청 형식이 올바르지 않습니다", "detail": [...]}` |
| 500 | 내부 서버 오류 | `{"error": "서버 오류가 발생했습니다"}` |
| 503 | RAG 검색 실패 | `{"error": "현재 정보 검색에 문제가 있습니다. 잠시 후 다시 시도해주세요"}` |

### POST /api/v1/chat/stream

SSE(Server-Sent Events) 방식으로 스트리밍 응답을 반환한다.

**요청**: `/api/v1/chat`과 동일

**응답 (200, text/event-stream)**:

```
data: {"type": "token", "content": "안녕"}
data: {"type": "token", "content": "하세요"}
data: {"type": "metadata", "identified_model": "770S", "intent": "troubleshoot"}
data: {"type": "done", "disclaimer_included": true}
```

## 2. 에러 코드 조회 엔드포인트

### GET /api/v1/models/{model_id}/errors/{error_code}

특정 기종의 에러 코드 정보를 직접 조회한다.

**경로 파라미터**:
- `model_id`: 기종 식별자 (270S, 580, 770S, 970S)
- `error_code`: 에러 코드 (예: E003)

**응답 (200)**:

```
{
  "code": string,
  "model_id": string,
  "title": string,
  "description": string,
  "cause": string,
  "support_level": "Level1" | "Level3",
  "resolution_steps": [string],
  "escalation_note": string | null
}
```

**오류 응답**:

| 코드 | 조건 | 본문 |
|------|------|------|
| 404 | 에러 코드가 해당 기종에 존재하지 않음 | `{"error": "해당 기종에서 에러 코드를 찾을 수 없습니다"}` |
| 400 | 지원하지 않는 기종 | `{"error": "지원하지 않는 기종입니다"}` |

### GET /api/v1/models/{model_id}/errors

특정 기종의 전체 에러 코드 목록을 반환한다.

**응답 (200)**:

```
{
  "model_id": string,
  "errors": [
    {
      "code": string,
      "title": string,
      "support_level": "Level1" | "Level3"
    }
  ],
  "total": number
}
```

## 3. 주변기기 호환 조회 엔드포인트

### GET /api/v1/models/{model_id}/peripherals

특정 기종의 호환 주변기기 목록을 반환한다.

**쿼리 파라미터**:
- `type` (선택): 주변기기 유형 필터 (printer, pc_software, barcode_reader)

**응답 (200)**:

```
{
  "model_id": string,
  "peripherals": [
    {
      "peripheral_name": string,
      "peripheral_type": string,
      "is_compatible": boolean,
      "connection_method": string | null,
      "notes": string | null
    }
  ],
  "total": number
}
```

### GET /api/v1/models/{model_id}/peripherals/{peripheral_name}/compatibility

특정 주변기기의 상세 호환 정보를 반환한다.

**응답 (200)**:

```
{
  "model_id": string,
  "peripheral_name": string,
  "peripheral_type": string,
  "is_compatible": boolean,
  "connection_method": string | null,
  "driver_version": string | null,
  "setup_steps": [string] | null,
  "notes": string | null
}
```

## 4. 기종 정보 엔드포인트

### GET /api/v1/models

지원되는 전체 기종 목록을 반환한다.

**응답 (200)**:

```
{
  "models": [
    {
      "model_id": string,
      "display_name": string,
      "tier": "entry" | "professional",
      "installation_type": "foldable" | "separable"
    }
  ]
}
```

### GET /api/v1/models/{model_id}

특정 기종의 상세 정보를 반환한다.

**응답 (200)**:

```
{
  "model_id": string,
  "display_name": string,
  "tier": "entry" | "professional",
  "installation_type": "foldable" | "separable",
  "tone_profile": "casual" | "professional",
  "measurement_items": [string],
  "supported_peripheral_types": [string]
}
```

## 5. 세션 관리 엔드포인트

### GET /api/v1/sessions/{thread_id}

대화 세션의 현재 상태를 반환한다.

**응답 (200)**:

```
{
  "thread_id": string,
  "identified_model": string | null,
  "model_tier": string | null,
  "message_count": number,
  "created_at": string (ISO 8601),
  "last_active_at": string (ISO 8601)
}
```

### DELETE /api/v1/sessions/{thread_id}

대화 세션을 종료하고 상태를 초기화한다.

**응답 (204)**: 본문 없음

## 6. 헬스 체크

### GET /api/v1/health

서비스 상태를 확인한다.

**응답 (200)**:

```
{
  "status": "healthy",
  "components": {
    "llm": "ok" | "degraded" | "down",
    "vector_db": "ok" | "degraded" | "down",
    "structured_db": "ok" | "degraded" | "down"
  }
}
```

## 7. 문서 관리 엔드포인트 (관리자 전용)

### POST /api/v1/documents/upload

기종별 PDF 문서를 업로드하고 벡터 DB에 인제스트한다.

**요청 (multipart/form-data)**:

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `model_id` | string | O | 기종 식별자 (270S, 580, 770S, 970S) 또는 "common" (공통 문서) |
| `category` | string | O | 문서 카테고리 (manual, printer_compatibility, measurement_precautions) |
| `file` | file | O | PDF 파일 |

**응답 (200)**:

```
{
  "model_id": string,
  "category": string,
  "filename": string,
  "chunk_count": number — 생성된 청크 수,
  "status": "ingested"
}
```

**오류 응답**:

| 코드 | 조건 | 본문 |
|------|------|------|
| 400 | 지원하지 않는 기종 또는 카테고리 | `{"error": "지원하지 않는 기종/카테고리입니다"}` |
| 400 | PDF가 아닌 파일 업로드 | `{"error": "PDF 파일만 업로드 가능합니다"}` |
| 500 | 인제스트 실패 | `{"error": "문서 인제스트 중 오류가 발생했습니다"}` |

**카테고리 규칙**:
- `manual`: 기종당 필수 (기종별 사용 매뉴얼)
- `printer_compatibility`: 선택 (기종별 프린터 호환리스트)
- `measurement_precautions`: 선택 (전 기종 공통 — `model_id`를 "common"으로 설정하면 모든 기종 검색에서 참조)

### GET /api/v1/documents

업로드된 문서 현황을 조회한다.

**쿼리 파라미터**:
- `model_id` (선택): 기종별 필터

**응답 (200)**:

```
{
  "documents": [
    {
      "model_id": string,
      "category": string,
      "filename": string,
      "chunk_count": number,
      "uploaded_at": string (ISO 8601)
    }
  ]
}
```

---

## Tool Calling 계약 (LangGraph 내부)

LangGraph 워크플로우 내에서 에이전트가 호출하는 도구 함수 계약이다. REST API로 직접 노출되지 않는다.

### lookup_error_code

```
입력: model (string), error_code (string)
출력: ErrorCode 객체 또는 "해당 에러 코드를 찾을 수 없습니다" 메시지
용도: 트러블슈팅 에이전트가 에러 코드 DB를 조회할 때 사용
```

### search_errors_by_symptom

```
입력: model (string), symptom_description (string)
출력: 관련 ErrorCode 목록 (최대 5건, 관련도순)
용도: 에러 코드 없이 증상만 보고된 경우 유사 에러 검색
```

### check_peripheral_compatibility

```
입력: model (string), peripheral_type (string), peripheral_name (string, 선택)
출력: PeripheralCompatibility 목록
용도: 연동 에이전트가 호환 주변기기를 조회할 때 사용
```

### search_manual

```
입력: model (string), category (string), query (string)
출력: ManualChunk 목록 (최대 5건, 관련도순)
용도: 설치/임상 방어 에이전트가 매뉴얼 본문을 검색할 때 사용
제약: model 필터는 반드시 적용 (기종 격리 원칙)
```
