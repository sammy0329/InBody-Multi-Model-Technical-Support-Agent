"""설치 에이전트 유틸리티 단위 테스트

설치 중 문제 감지 로직을 검증한다.
"""

import pytest

from src.graph.nodes.install_agent import INSTALL_TROUBLE_KEYWORDS, _is_install_trouble


@pytest.mark.unit
@pytest.mark.parametrize("keyword", INSTALL_TROUBLE_KEYWORDS)
def test_install_trouble_positive(keyword):
    """INSTALL_TROUBLE_KEYWORDS에 포함된 키워드가 있으면 True를 반환한다."""
    message = f"설치 중에 {keyword} 상황입니다"
    assert _is_install_trouble(message) is True


NON_TROUBLE_MESSAGES = [
    "270S 설치 순서를 알려주세요",
    "접이식 조립 방법이 궁금합니다",
    "분리형 기기의 설치 안내 부탁합니다",
    "초기 세팅은 어떻게 하나요",
]


@pytest.mark.unit
@pytest.mark.parametrize("message", NON_TROUBLE_MESSAGES)
def test_install_trouble_negative(message):
    """문제 키워드가 없는 일반 설치 질문은 False를 반환한다."""
    assert _is_install_trouble(message) is False
