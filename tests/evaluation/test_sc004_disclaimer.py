"""SC-004 평가: 임상 응답 의학적 면책 문구 삽입률 = 100%

needs_disclaimer=True인 임상 응답 20개에 대해
가드레일의 면책 문구 자동 삽입이 100% 작동하는지 측정한다.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.graph.nodes.guardrail import guardrail_node
from src.prompts.disclaimers import MEDICAL_DISCLAIMER

MOCK_LLM_PASS = '{"passed": true, "violations": [], "suggestion": ""}'

SC004_CLINICAL_ANSWERS = [
    "체지방률은 건강의 지표로 사용됩니다.",
    "BMI가 25 이상이면 과체중으로 분류됩니다.",
    "골격근량은 기초대사량에 영향을 줍니다.",
    "내장지방레벨이 높으면 주의가 필요합니다.",
    "체수분량은 세포내수분과 세포외수분으로 나뉩니다.",
    "ECW/TBW 비율이 0.39 이상이면 부종을 의심할 수 있습니다.",
    "위상각은 세포막의 건강 상태를 반영합니다.",
    "부위별 근육량 분석으로 균형을 확인할 수 있습니다.",
    "체지방량이 높고 골격근량이 낮으면 C형 체형입니다.",
    "기초대사량은 나이, 성별, 근육량에 따라 달라집니다.",
    "단백질량은 영양 상태를 반영합니다.",
    "무기질량은 골밀도와 관련이 있습니다.",
    "내장지방면적은 복부비만의 지표입니다.",
    "세포외수분비가 높은 것은 여러 원인이 있을 수 있습니다.",
    "체성분 분석 결과는 측정 조건에 따라 달라질 수 있습니다.",
    "식후 2시간 이내에는 측정을 피하는 것이 좋습니다.",
    "운동 직후에는 체수분 변화로 결과가 달라질 수 있습니다.",
    "여성의 경우 생리 주기에 따라 수분량이 변동됩니다.",
    "아침에 측정하면 가장 일관된 결과를 얻을 수 있습니다.",
    "약물 복용 시 체수분에 영향을 줄 수 있습니다.",
]


def _base_state(answer: str, needs_disclaimer: bool = True):
    return {
        "messages": [],
        "identified_model": "270S",
        "model_tier": "entry",
        "intent": "clinical",
        "retrieved_docs": [],
        "image_urls": [],
        "error_code": None,
        "support_level": None,
        "tone_profile": "casual",
        "needs_disclaimer": needs_disclaimer,
        "answer": answer,
        "guardrail_passed": None,
        "guardrail_retry_count": 0,
        "guardrail_violations": [],
        "guardrail_suggestion": None,
    }


@pytest.mark.evaluation
@pytest.mark.sc004
@pytest.mark.parametrize(
    "clinical_answer",
    SC004_CLINICAL_ANSWERS,
    ids=[f"sc004_{i:02d}" for i in range(len(SC004_CLINICAL_ANSWERS))],
)
@patch("src.graph.nodes.guardrail.ChatOpenAI")
async def test_sc004_disclaimer_always_present(mock_cls, clinical_answer, sc_metrics):
    """SC-004: needs_disclaimer=True인 임상 응답에 면책 문구가 100% 삽입된다."""
    mock_instance = AsyncMock()
    mock_instance.ainvoke.return_value.content = MOCK_LLM_PASS
    mock_cls.return_value = mock_instance

    state = _base_state(clinical_answer, needs_disclaimer=True)
    result = await guardrail_node(state)

    passed = MEDICAL_DISCLAIMER in result["answer"]
    sc_metrics.record("SC-004", passed)
    assert passed, f"면책 문구 누락: {result['answer'][:100]}..."
