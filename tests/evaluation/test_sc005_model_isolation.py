"""SC-005 평가: 기종 간 정보 오염(누출) 발생률 = 0%

4x4=16 기종 조합에 대해 교차 기종 정보가 가드레일에서 올바르게
감지(차단)/허용되는지 측정한다.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.graph.nodes.guardrail import guardrail_node
from src.models.inbody_models import SUPPORTED_MODELS

MOCK_LLM_PASS = '{"passed": true, "violations": [], "suggestion": ""}'

# 교차 기종 조합: (identified_model, mentioned_model, should_block)
ISOLATION_CASES = []
for model in sorted(SUPPORTED_MODELS):
    for other in sorted(SUPPORTED_MODELS):
        if model != other:
            ISOLATION_CASES.append((model, other, True))  # 다른 기종 → 차단
        else:
            ISOLATION_CASES.append((model, other, False))  # 같은 기종 → 허용


def _base_state(identified_model: str, answer: str):
    return {
        "messages": [],
        "identified_model": identified_model,
        "model_tier": "entry",
        "intent": "troubleshoot",
        "retrieved_docs": [],
        "image_urls": [],
        "error_code": None,
        "support_level": None,
        "tone_profile": "casual",
        "needs_disclaimer": False,
        "answer": answer,
        "guardrail_passed": None,
        "guardrail_retry_count": 0,
        "guardrail_violations": [],
        "guardrail_suggestion": None,
    }


@pytest.mark.evaluation
@pytest.mark.sc005
@pytest.mark.parametrize(
    "identified, mentioned, should_block",
    ISOLATION_CASES,
    ids=[f"sc005_{id}_{men}_{'block' if blk else 'allow'}"
         for id, men, blk in ISOLATION_CASES],
)
@patch("src.graph.nodes.guardrail.ChatOpenAI")
async def test_sc005_model_isolation(mock_cls, identified, mentioned, should_block, sc_metrics):
    """SC-005: 교차 기종 정보가 정확히 감지/허용된다."""
    mock_instance = AsyncMock()
    mock_instance.ainvoke.return_value.content = MOCK_LLM_PASS
    mock_cls.return_value = mock_instance

    # 모델명 뒤에 공백을 두어 \b 경계가 올바르게 매칭되도록 한다
    answer = f"InBody {mentioned} 설치 방법은 다음과 같습니다."
    state = _base_state(identified, answer)
    result = await guardrail_node(state)

    violations = result.get("guardrail_violations", [])
    has_isolation_violation = any("기종 격리 위반" in v for v in violations)

    if should_block:
        # 다른 기종: 격리 위반이 감지되어야 한다
        passed = has_isolation_violation
    else:
        # 같은 기종: 격리 위반이 없어야 한다
        passed = not has_isolation_violation

    sc_metrics.record("SC-005", passed)
    assert passed, (
        f"identified={identified}, mentioned={mentioned}, "
        f"should_block={should_block}, isolation_violation={has_isolation_violation}"
    )
