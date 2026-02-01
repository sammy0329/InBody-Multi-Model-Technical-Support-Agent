"""트러블슈팅 유틸리티 단위 테스트 — SC-009 보조

에러 코드 추출과 에스컬레이션 감지의 정확성을 검증한다.
"""

import pytest

from src.graph.nodes.troubleshoot_agent import (
    ESCALATION_KEYWORDS,
    _extract_error_code,
    _is_escalation,
)


# ── _extract_error_code: E 형식 ──

ERROR_CODE_E_FORMAT = [
    ("E001", "E001"),
    ("e001", "E001"),
    ("E123", "E123"),
    ("e999", "E999"),
    ("E013 에러가 떠요", "E013"),
    ("270S에서 E001 에러 발생", "E001"),
]


@pytest.mark.unit
@pytest.mark.parametrize("message, expected", ERROR_CODE_E_FORMAT)
def test_extract_error_code_e_format(message, expected):
    """E+3자리 형식의 에러 코드를 정확히 추출한다."""
    assert _extract_error_code(message) == expected


# ── _extract_error_code: 한국어 형식 ──

ERROR_CODE_KOREAN_FORMAT = [
    ("에러 001이 나타나요", "E001"),
    ("에러코드 003이 떠요", "E003"),
    ("오류 456 발생", "E456"),
    ("오류코드 789가 표시됩니다", "E789"),
]


@pytest.mark.unit
@pytest.mark.parametrize("message, expected", ERROR_CODE_KOREAN_FORMAT)
def test_extract_error_code_korean_format(message, expected):
    """한국어 에러/오류 키워드 + 숫자 형식을 추출한다."""
    assert _extract_error_code(message) == expected


# ── _extract_error_code: None 반환 ──

ERROR_CODE_NONE_CASES = [
    "화면이 안 켜져요",
    "측정이 이상해요",
    "설치 방법 알려주세요",
    "프린터 연결 안 돼요",
]


@pytest.mark.unit
@pytest.mark.parametrize("message", ERROR_CODE_NONE_CASES)
def test_extract_error_code_returns_none(message):
    """에러 코드 패턴이 없으면 None을 반환한다."""
    assert _extract_error_code(message) is None


# ── _is_escalation: 긍정 케이스 ──


@pytest.mark.unit
@pytest.mark.parametrize("keyword", ESCALATION_KEYWORDS)
def test_is_escalation_positive(keyword):
    """에스컬레이션 키워드가 포함되면 True를 반환한다."""
    message = f"위의 방법으로 {keyword} 상태입니다"
    assert _is_escalation(message) is True


# ── _is_escalation: 부정 케이스 ──

NON_ESCALATION_MESSAGES = [
    "270S 설치 방법 알려주세요",
    "체지방률이 높은데요",
    "처음 사용합니다",
    "프린터 연결하고 싶어요",
    "에러코드 E001이 떠요",
]


@pytest.mark.unit
@pytest.mark.parametrize("message", NON_ESCALATION_MESSAGES)
def test_is_escalation_negative(message):
    """에스컬레이션 키워드가 없으면 False를 반환한다."""
    assert _is_escalation(message) is False
