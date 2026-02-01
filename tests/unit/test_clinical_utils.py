"""임상 에이전트 유틸리티 단위 테스트

의학적 진단 요청 감지 로직을 검증한다.
"""

import pytest

from src.graph.nodes.clinical_agent import DIAGNOSIS_KEYWORDS, _detect_diagnosis_request


@pytest.mark.unit
@pytest.mark.parametrize("keyword", DIAGNOSIS_KEYWORDS)
def test_detect_diagnosis_positive(keyword):
    """DIAGNOSIS_KEYWORDS에 포함된 키워드가 있으면 True를 반환한다."""
    message = f"이 측정 결과로 {keyword}을 알 수 있나요?"
    assert _detect_diagnosis_request(message) is True


NON_DIAGNOSIS_MESSAGES = [
    "체지방률 확인해 주세요",
    "BMI 수치가 궁금합니다",
    "골격근량 결과를 해석해 주세요",
    "270S 설치 방법 알려주세요",
    "프린터 연결이 안 돼요",
]


@pytest.mark.unit
@pytest.mark.parametrize("message", NON_DIAGNOSIS_MESSAGES)
def test_detect_diagnosis_negative(message):
    """진단 키워드가 없는 일반 메시지는 False를 반환한다."""
    assert _detect_diagnosis_request(message) is False
