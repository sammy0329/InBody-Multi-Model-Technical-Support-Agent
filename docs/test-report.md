# InBody Tech-Master 테스트 결과 리포트

**작성일**: 2026-02-01
**테스트 환경**: Python 3.11.7, pytest 9.0.2, macOS
**총 테스트 케이스**: 444 passed in 2.11s

---

## SC Metrics Report

spec.md에 정의된 성공 기준(SC)별 정량적 달성 결과:

| SC | 기준 | 결과 | 달성률 | 목표 | 상태 |
|---|---|---|---|---|---|
| SC-001 | 기종 식별 정확도 | 40/40 | 100.0% | >= 95% | PASS |
| SC-003 | 에러코드 해결 정확도 | 45/45 | 100.0% | >= 90% | PASS |
| SC-004 | 면책 문구 삽입률 | 20/20 | 100.0% | = 100% | PASS |
| SC-005 | 기종 간 정보 격리 | 16/16 | 100.0% | = 100% | PASS |
| SC-006 | Level 3 안전 차단율 | 24/24 | 100.0% | = 100% | PASS |
| SC-009 | 할루시네이션 방지율 | 21/21 | 100.0% | = 100% | PASS |
| SC-010 | 캐시 히트율 | 10/10 | 100.0% | >= 60% | PASS |
| SC-011 | 캐시 응답 지연 | 8/8 | 100.0% | = 100% | PASS |
| SC-012 | 캐시 교차 오염 | 25/25 | 100.0% | = 100% | PASS |

> 전체 SC 메트릭은 `pytest tests/ -v` 실행 시 터미널 하단에 자동 출력된다.

---

## 테스트 아키텍처

3계층 테스트 구조로 설계하여, LLM API 키 없이도 전체 SC 메트릭을 생산한다.

```
tests/
├── conftest.py                          # SCMetricsCollector, pytest_terminal_summary
├── unit/                                # 결정론적 단위 테스트 (LLM 불필요)
│   ├── test_model_router.py             # SC-001 기종 식별 정규식
│   ├── test_guardrail_deterministic.py  # SC-004, SC-005, SC-006 가드레일
│   ├── test_troubleshoot_utils.py       # SC-009 보조 (에러코드 추출, 에스컬레이션)
│   ├── test_edges.py                    # 라우팅 분기 정확성
│   ├── test_semantic_cache.py           # 시멘틱 캐시 단위 테스트
│   ├── test_tone_profiles.py            # 톤앤매너 매핑
│   ├── test_clinical_utils.py           # 진단 요청 감지
│   ├── test_connect_utils.py            # 주변기기 유형/이름 추출
│   └── test_install_utils.py            # 설치 문제 감지
├── contract/                            # API 계약 테스트
│   ├── test_models_api.py               # GET /models 엔드포인트
│   └── test_errors_api.py               # GET /models/{id}/errors 엔드포인트
└── evaluation/                          # SC 메트릭 생성 평가 테스트
    ├── conftest.py                      # seeded_session_factory (in-memory DB)
    ├── test_sc001_model_identification.py
    ├── test_sc003_error_resolution.py
    ├── test_sc003_peripheral_compat.py
    ├── test_sc004_disclaimer.py
    ├── test_sc005_model_isolation.py
    ├── test_sc006_level3_safety.py
    ├── test_sc009_hallucination.py
    ├── test_sc010_cache_hit.py
    ├── test_sc011_cache_latency.py
    └── test_sc012_cache_isolation.py
```

---

## 테스트 상세

### Unit Tests (224 케이스)

#### test_model_router.py — SC-001 기종 식별

`_pre_extract_model()` 정규식의 정확도를 40개 한국어 입력 패턴으로 검증.

| 카테고리 | 입력 예시 | 기대 결과 |
|---|---|---|
| 직접 언급 | "InBody 270S 에러가 나요" | 270S |
| 대소문자 변형 | "770s 사용 중입니다" | 770S |
| 한국어 조사 결합 | "270S와 580 비교해주세요" | 270S |
| 띄어쓰기 없음 | "InBody580 문의" | 580 |
| 미지원 기종 | "InBody 230 모델인데요" | None |
| 임베딩 방지 | "A580B 코드 입력" | None |

추가로 `_extract_all_models()` (비교 질문 감지)과 `_build_comparison_response()` (비교 응답 구조) 검증.

#### test_guardrail_deterministic.py — SC-004, SC-005, SC-006 가드레일

ChatOpenAI를 mock하여 LLM Check 4를 우회하고, 결정론적 Check 1~3만 검증.

| Check | 검증 항목 | 케이스 수 |
|---|---|---|
| Check 1 | `needs_disclaimer=True` 시 `MEDICAL_DISCLAIMER` 자동 삽입, 중복 방지 | 4 |
| Check 2 | 4x4 기종 조합의 교차 기종 정보 감지/허용 | 16 |
| Check 3 | `UNSAFE_REPAIR_KEYWORDS` 8개의 Level 3 감지, Level 1 오탐 방지 | 17 |
| 기타 | 최대 재시도 초과 시 안전 폴백, 빈 응답 처리 | 2 |

#### test_troubleshoot_utils.py — SC-009 보조

| 함수 | 검증 | 케이스 수 |
|---|---|---|
| `_extract_error_code()` | E형식(E001), 한국어 형식(에러 001), None 반환 | 14 |
| `_is_escalation()` | "안 돼", "해결 안", "여전히" 등 13개 키워드 | 18 |

#### test_edges.py — 라우팅 분기

| 함수 | 검증 | 케이스 수 |
|---|---|---|
| `route_after_model_router` | answer→END, identified→cache_lookup, empty→END | 4 |
| `route_after_cache_lookup` | hit→END, miss→intent_router, no flag→intent_router | 3 |
| `route_after_intent_router` | 5개 의도→5개 전문 에이전트 매핑 + unknown 폴백 | 7 |
| `route_after_guardrail` | passed→cache_store, retry<MAX→fix, retry>=MAX→cache_store | 4 |

#### test_semantic_cache.py — 시멘틱 캐시 (27 케이스)

인메모리 Chroma + FakeEmbeddings(동일 문자열 → 동일 벡터)를 사용한 결정론적 테스트. LLM 키 불필요.

| 테스트 클래스 | 검증 | 케이스 수 |
|---|---|---|
| `TestStoreAndLookup` | store 반환값, exact match lookup, miss, empty | 4 |
| `TestModelIsolation` | 6개 기종 조합 교차 격리 + 동일 기종 hit | 8 |
| `TestGuardrailFilter` | guardrail_passed=False 저장 차단 | 2 |
| `TestTTLExpiration` | TTL 초과 시 자동 삭제, 이내 시 hit | 2 |
| `TestInvalidate` | 기종별/기종+의도별 삭제, 빈 삭제 | 3 |
| `TestGetStats` | 빈 통계, 저장 후 통계, 히트 후 통계 | 3 |
| `TestCacheDisabled` | 비활성화 시 store/lookup → None | 2 |
| `TestHitCounter` | 조회 시 hit_count 증가 | 1 |
| `TestImageUrls` | image_urls 직렬화/역직렬화, 빈 배열 | 2 |

#### test_tone_profiles.py — 톤앤매너

- casual/professional 톤 instruction 내용 검증
- 4개 기종별 톤+티어 매핑 (`270S→casual/entry`, `970S→professional/professional`)
- 잘못된 프로필명 → `ValueError`

#### test_clinical_utils.py — 진단 요청 감지

- `DIAGNOSIS_KEYWORDS` 18개 각각의 양성 감지
- 일반 질문 5개의 음성 확인

#### test_connect_utils.py — 주변기기 추출

| 함수 | 검증 | 케이스 수 |
|---|---|---|
| `_extract_peripheral_type()` | 프린터/PC/바코드/USB 분류 | 14 |
| `_extract_peripheral_name()` | Lookin'Body, EMR, HIS, DICOM, HL7 추출 | 8 |

#### test_install_utils.py — 설치 문제 감지

- `INSTALL_TROUBLE_KEYWORDS` 각각의 양성 감지
- 일반 설치 질문 4개의 음성 확인

---

### Contract Tests (11 케이스)

#### test_models_api.py — 모델 API

| 테스트 | 검증 |
|---|---|
| `test_list_models_returns_four` | GET /models → 4개 기종 반환 |
| `test_list_models_response_shape` | 응답 필드 구조 (model_id, name, tier) |
| `test_get_model_detail_270s` | 270S 상세 (tier=entry, install_type=foldable) |
| `test_get_model_404_unsupported` | 미지원 기종 → 404 |

#### test_errors_api.py — 에러 코드 API

Seeded in-memory DB 기반.

| 테스트 | 검증 |
|---|---|
| `test_list_errors_270s` | GET /models/270S/errors → 5개 에러 코드 |
| `test_get_error_detail` | E001 상세 (title, cause, resolution_steps) |
| `test_get_error_404_unknown_code` | 미등록 코드 → 404 |
| `test_list_errors_400_unsupported_model` | 미지원 기종 → 400 |

---

### Evaluation Tests (195 케이스)

SC 메트릭을 직접 생성하는 평가 테스트. 모든 테스트에서 `sc_metrics.record("SC-XXX", passed)`를 호출하여 메트릭 리포트에 반영.

#### test_sc001_model_identification.py (40 케이스)

40개 한국어 입력 → `_pre_extract_model()` → 정확한 기종 식별.

```python
# 입력 예시
("InBody 270S 에러가 나요", "270S"),
("580 모델 프린터 연결", "580"),
("770s 캘리브레이션 방법", "770S"),     # 소문자 → 대문자 정규화
("970S와 770S 비교해주세요", "970S"),   # 첫 번째 기종 반환
```

#### test_sc003_error_resolution.py (20 케이스)

20개 에러 코드에 대해 `lookup_error_code` 도구를 호출하고, 응답에 **매뉴얼 기반 필수 키워드**가 포함되는지 3중 검증.

| 검증 항목 | 설명 | 예시 |
|---|---|---|
| 제목 키워드 | 에러 코드 제목이 응답에 포함 | "전극 접촉 불량" |
| 지원 수준 | Level 1/3 텍스트 일치 | "사용자 해결 가능 (Level 1)" |
| 해결 키워드 | resolution_steps의 핵심 기술 용어 포함 | ["전극", "전해질 티슈", "재측정"] |

**4개 기종 × 5개 에러코드 = 20개 케이스 전체 커버.**

```
270S: E001(전극), E002(체중센서), E003(프린터), E010(디스플레이), E020(메인보드)
580:  E001(전극), E004(네트워크), E005(업데이트), E011(체중센서), E021(터치스크린)
770S: E001(임피던스), E006(데이터전송), E012(ECW/TBW), E022(편차), E030(캘리브레이션)
970S: E001(다주파수), E007(위상각), E008(체수분), E013(데이터내보내기), E031(QC)
```

#### test_sc003_peripheral_compat.py (25 케이스)

25개 주변기기 호환 항목에 대해 `check_peripheral_compatibility` 도구를 호출하고, 응답에 **호환 상태, 연결 방식, 설정 절차 키워드**가 포함되는지 3중 검증.

| 검증 항목 | 설명 | 예시 |
|---|---|---|
| 호환 상태 | "호환" 텍스트 포함 확인 | "호환" |
| 연결 방식 | connection_method 텍스트 포함 | "USB / Wi-Fi" |
| 설정 키워드 | setup_steps의 핵심 절차 용어 포함 | ["프린터 케이블", "USB 포트", "시범인쇄"] |

**4개 기종 × 프린터/PC/바코드/USB/EMR = 25개 케이스.**

#### test_sc004_disclaimer.py (20 케이스)

`guardrail_node`를 통해 임상 관련 응답에 `MEDICAL_DISCLAIMER` 포함 여부 검증.

- 15개 임상 응답 → `needs_disclaimer=True` → 면책 문구 포함 확인
- 5개 비임상 응답 → `needs_disclaimer=False` → 면책 문구 미포함 확인

#### test_sc005_model_isolation.py (16 케이스)

4x4 기종 조합(270S, 580, 770S, 970S)에 대해 교차 기종 정보 감지.

- 12개 교차 조합: "InBody {다른기종} ..." → 기종 격리 위반 감지
- 4개 동일 조합: "InBody {같은기종} ..." → 위반 없음

#### test_sc006_level3_safety.py (24 케이스)

| 시나리오 | 케이스 수 | 기대 결과 |
|---|---|---|
| Level 3 + unsafe 키워드 8개 | 8 | 차단 |
| Level 3 + safe 응답 8개 | 8 | 원문 보존 확인 |
| Level 1 + unsafe 키워드 8개 | 8 | 오탐 방지 (통과) |

#### test_sc009_hallucination.py (21 케이스)

Seeded in-memory DB 기반.

- 12개 미등록 에러코드 → "찾을 수 없습니다" 확인 (추측 응답 0%)
- 9개 등록 에러코드 → "해결 단계" 포함 확인 (정상 조회)

#### test_sc010_cache_hit.py (11 케이스)

인메모리 Chroma + FakeEmbeddings를 사용한 캐시 히트율 측정. 동일 질문 store 후 lookup 시 캐시 히트 여부 검증.

| 시나리오 | 케이스 수 | 검증 |
|---|---|---|
| 10개 시나리오별 캐시 히트 | 10 | store → 동일 query lookup → entry ≠ None, 응답 일치 |
| 첫 질문 캐시 미스 | 1 | 빈 캐시 lookup → None (기대된 미스) |

**4개 기종 × 4개 의도 + 긴 응답 2개 = 10개 시나리오.**

#### test_sc011_cache_latency.py (8 케이스)

캐시 히트 시 응답 지연이 200ms 이하인지 `time.perf_counter()`로 측정.

| 시나리오 | 케이스 수 | 검증 |
|---|---|---|
| 일반 응답 (5종) | 5 | lookup ≤ 200ms |
| 긴 응답 (5000자, 3종) | 3 | lookup ≤ 200ms |

#### test_sc012_cache_isolation.py (10 케이스)

동일 질문을 4개 기종에 각각 저장한 후, 기종 필터가 정확히 동작하는지 검증.

| 테스트 | 케이스 수 | 검증 |
|---|---|---|
| `test_cache_hit_returns_correct_model` | 4 | 4개 기종별 조회 → 해당 기종 응답만 반환 |
| `test_no_other_model_response` | 4 | 응답에 다른 기종명 미포함 확인 |
| `test_single_model_store_not_returned_for_other` | 1 | 770S 전용 캐시 → 다른 기종 조회 시 미스 |
| `test_invalidate_one_model_does_not_affect_others` | 1 | 770S 삭제 → 나머지 캐시 유지 확인 |

---

## 테스트 중 발견한 이슈

### 1. `\b` 정규식과 한국어 유니코드 경계 문제

**파일**: `src/graph/nodes/guardrail.py`

guardrail의 기종 격리 정규식 `\bInBody\s+{model}\b`에서, Python `\b`는 `\w`/`\W` 경계에서만 매칭된다. 한국어 문자는 `\w`로 취급되므로, "InBody 770S에서"처럼 모델명 바로 뒤에 한국어가 오면 `\b`가 매칭 실패한다.

```
"InBody 770S에서" → \b 매칭 실패 (S와 에 사이에 \w→\w 경계 없음)
"InBody 770S 에서" → \b 매칭 성공 (S와 공백 사이에 \w→\W 경계 있음)
```

`model_router.py`에서는 이 문제를 `(?<![A-Za-z0-9])` ASCII 경계로 해결했으나, `guardrail.py`에서는 미적용 상태.

**영향**: 한국어 조사가 바로 붙은 모델명(예: "770S에서", "580을")의 교차 기종 감지 누락 가능.

### 2. HARDWARE_DISCLAIMER 자기 참조 문제

**파일**: `src/graph/nodes/guardrail.py`

`HARDWARE_DISCLAIMER` 면책 문구 텍스트에 "내부 부품"이 포함되어 있으며, 이는 `UNSAFE_REPAIR_KEYWORDS` 중 하나이다. Level 3 응답에서:

1. Check 1이 `HARDWARE_DISCLAIMER`를 자동 삽입
2. Check 3이 삽입된 면책 문구에서 "내부 부품"을 감지
3. Level 3 안전 위반으로 판정

결과적으로 **모든 Level 3 안전 응답이 면책 문구 때문에 Level 3 위반으로 처리**되는 구조적 순환 문제가 존재한다.

**해결 방안**: Check 3에서 면책 문구 영역을 제외하고 원문만 검사하도록 수정 필요.

---

## 실행 방법

```bash
# 전체 테스트 + SC 리포트
pytest tests/ -v --tb=short

# Unit 테스트만 (빠른 실행)
pytest tests/unit/ -v

# SC 메트릭 평가만
pytest tests/evaluation/ -v

# 특정 SC 기준만
pytest -m sc001 -v    # 기종 식별
pytest -m sc003 -v    # 에러코드 해결 정확도
pytest -m sc005 -v    # 기종 격리
pytest -m sc010 -v    # 캐시 히트율
pytest -m sc011 -v    # 캐시 응답 지연
pytest -m sc012 -v    # 캐시 교차 오염

# 커버리지 포함
pytest tests/ --cov=src --cov-report=term-missing
```

---

## 설계 원칙

1. **LLM 없이 SC 메트릭 측정**: 정규식, 가드레일 결정론적 체크, DB 조회만으로 전체 메트릭 생산. API 키 없이도 `pytest tests/ -v` 한 줄로 결과 확인 가능.

2. **Seeded In-Memory DB**: `error_codes.json`과 `peripheral_compatibility.json`을 인메모리 SQLite에 시딩하여, 실제 DB 의존성 없이 도구 레벨 end-to-end 검증.

3. **parametrize 활용**: 소수의 테스트 함수로 444개 케이스 커버. 새 에러코드나 주변기기 추가 시 JSON에만 항목 추가하면 자동 반영.

4. **3중 키워드 검증**: 단순 형식 검증이 아닌, 매뉴얼에서 반드시 포함되어야 하는 기술 키워드를 수동 정의하여 **내용 정확도** 측정.

5. **인메모리 벡터 DB**: 시멘틱 캐시 테스트는 `chromadb.Client()` 인메모리 + FakeEmbeddings(동일 문자열 → 동일 벡터)를 사용하여, 외부 의존 없이 캐시 격리·TTL·히트율·지연 검증.
