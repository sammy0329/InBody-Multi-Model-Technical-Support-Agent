"""ModelRouter 단위 테스트 — SC-001 기종 식별 정확도

순수 함수(_pre_extract_model, _extract_all_models, _build_comparison_response)를
LLM 없이 결정론적으로 검증한다.
"""

import pytest

from src.graph.nodes.model_router import (
    _build_comparison_response,
    _extract_all_models,
    _pre_extract_model,
)
from src.models.inbody_models import INBODY_MODELS, SUPPORTED_MODELS


# ── _pre_extract_model: 정규식 기종 식별 ──

PRE_EXTRACT_CASES = [
    # 직접 언급
    ("InBody 270S 설치 방법 알려주세요", "270S"),
    ("270S 에러 코드 E001", "270S"),
    ("InBody 580 측정 결과 해석", "580"),
    ("580 프린터 연결 안 돼요", "580"),
    ("InBody 770S 캘리브레이션", "770S"),
    ("770S ECW/TBW 비율 확인", "770S"),
    ("InBody 970S 위상각 해석", "970S"),
    ("970S QC 실패", "970S"),
    # 대소문자 변형
    ("인바디 270s 사용법", "270S"),
    ("770s 부위별 근육량", "770S"),
    ("970s 다주파수 임피던스", "970S"),
    ("inbody 580 연결", "580"),
    # 한국어 조사 결합 (ASCII 경계 테스트)
    ("270S와 관련된 질문입니다", "270S"),
    ("580을 사용하고 있는데요", "580"),
    ("770S에서 에러가 납니다", "770S"),
    ("970S에 대해 알려주세요", "970S"),
    ("270S의 장단점", "270S"),
    ("580은 어떤 기종인가요", "580"),
    ("770S가 좋은 이유", "770S"),
    ("970S를 구매했는데", "970S"),
    # 문맥 속 기종명
    ("체육관에서 270S 사용하고 있는데 에러가 납니다", "270S"),
    ("학교 체력 측정실에 580이 설치되어 있어요", "580"),
    ("연구실에서 770S로 실험 중입니다", "770S"),
    ("병원에서 970S 결과지가 인쇄 안 돼요", "970S"),
    # 비공식적 표현
    ("제가 쓰는 건 270S인데요", "270S"),
    ("우리 병원 580", "580"),
    ("770S 모델 사용자입니다", "770S"),
    ("970S 장비 관련 문의", "970S"),
    # 추가 한국어 조사
    ("270S에서는 체수분량 측정이 되나요", "270S"),
    ("580도 부위별 측정이 가능한가요", "580"),
    ("770S만 가지고 있어요", "770S"),
    ("970S부터는 위상각이 있나요", "970S"),
]


@pytest.mark.unit
@pytest.mark.parametrize(
    "message, expected",
    PRE_EXTRACT_CASES,
    ids=[f"case_{i}" for i in range(len(PRE_EXTRACT_CASES))],
)
def test_pre_extract_model(message, expected):
    """정규식 기반 기종 식별이 다양한 한국어 표현에서 정확히 작동한다."""
    result = _pre_extract_model(message)
    assert result == expected, f"입력: {message!r}, 기대: {expected}, 실제: {result}"


# ── _pre_extract_model: None 반환 케이스 ──

PRE_EXTRACT_NONE_CASES = [
    "안녕하세요",
    "InBody 사용법 알려주세요",
    "체성분 분석기 문제가 있어요",
    "InBody 230 모델인데요",
    "InBody 370 사용 중입니다",
    "InBody 120 에러",
]


@pytest.mark.unit
@pytest.mark.parametrize("message", PRE_EXTRACT_NONE_CASES)
def test_pre_extract_model_returns_none(message):
    """지원 기종명이 없는 메시지에서는 None을 반환한다."""
    assert _pre_extract_model(message) is None


# ── _pre_extract_model: 오탐 방지 ──

FALSE_POSITIVE_CASES = [
    "A580B 코드 입력",  # 알파벳으로 둘러싸인 경우
    "12345 에러",  # 숫자 속 패턴
]


@pytest.mark.unit
@pytest.mark.parametrize("message", FALSE_POSITIVE_CASES)
def test_pre_extract_model_no_false_positive(message):
    """ASCII 경계를 넘어선 패턴은 매칭하지 않는다."""
    assert _pre_extract_model(message) is None


# ── _extract_all_models: 복수 기종 추출 ──


@pytest.mark.unit
def test_extract_all_models_single():
    """단일 기종 언급 시 1개 원소 리스트를 반환한다."""
    assert _extract_all_models("270S 설치 방법") == ["270S"]


@pytest.mark.unit
def test_extract_all_models_multiple():
    """복수 기종 언급 시 순서를 유지하며 추출한다."""
    assert _extract_all_models("270S와 580 차이점") == ["270S", "580"]
    assert _extract_all_models("770S랑 970S 비교") == ["770S", "970S"]


@pytest.mark.unit
def test_extract_all_models_three():
    """3개 이상 기종 언급도 정확히 추출한다."""
    result = _extract_all_models("270s 580 770s 다 알려줘")
    assert result == ["270S", "580", "770S"]


@pytest.mark.unit
def test_extract_all_models_deduplication():
    """동일 기종 반복 언급 시 중복을 제거한다."""
    assert _extract_all_models("270S 270s 270S 확인") == ["270S"]


@pytest.mark.unit
def test_extract_all_models_empty():
    """기종명이 없는 메시지에서는 빈 리스트를 반환한다."""
    assert _extract_all_models("체성분 분석 방법") == []


# ── _build_comparison_response: 비교 응답 구조 ──


@pytest.mark.unit
def test_build_comparison_response_contains_models():
    """비교 응답에 요청한 기종들의 정보가 포함된다."""
    result = _build_comparison_response(["270S", "580"])
    assert "270S" in result
    assert "580" in result
    assert "요청하신 270S, 580" in result


@pytest.mark.unit
def test_build_comparison_response_contains_tier():
    """비교 응답에 기종별 분류(보급형/전문가용)가 포함된다."""
    result = _build_comparison_response(["270S", "970S"])
    assert "보급형" in result
    assert "전문가용" in result


@pytest.mark.unit
def test_build_comparison_response_all_four():
    """4개 기종 전체 비교 시 모든 기종 정보가 포함된다."""
    result = _build_comparison_response(["270S", "580", "770S", "970S"])
    for model_id in SUPPORTED_MODELS:
        assert model_id in result
        assert INBODY_MODELS[model_id].name in result
