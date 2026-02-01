"""워크플로우 엣지 라우팅 단위 테스트

edges.py의 4개 라우팅 함수가 상태에 따라 올바른 노드를 반환하는지 검증한다.
"""

import pytest

from src.graph.edges import (
    MAX_GUARDRAIL_RETRIES,
    route_after_cache_lookup,
    route_after_guardrail,
    route_after_intent_router,
    route_after_model_router,
)


# ── route_after_model_router ──


@pytest.mark.unit
def test_model_router_answer_ends():
    """answer가 설정되면 __end__로 라우팅한다."""
    assert route_after_model_router({"answer": "비교 결과"}) == "__end__"


@pytest.mark.unit
def test_model_router_identified_goes_to_cache_lookup():
    """identified_model이 설정되면 cache_lookup으로 라우팅한다."""
    assert route_after_model_router({"identified_model": "270S"}) == "cache_lookup"


@pytest.mark.unit
def test_model_router_empty_ends():
    """상태가 비어있으면 __end__로 라우팅한다."""
    assert route_after_model_router({}) == "__end__"


@pytest.mark.unit
def test_model_router_answer_takes_priority():
    """answer와 identified_model 둘 다 있으면 answer 우선 → __end__."""
    state = {"answer": "something", "identified_model": "270S"}
    assert route_after_model_router(state) == "__end__"


# ── route_after_cache_lookup ──


@pytest.mark.unit
def test_cache_lookup_hit_ends():
    """cache_hit=True이면 __end__로 라우팅한다."""
    assert route_after_cache_lookup({"cache_hit": True}) == "__end__"


@pytest.mark.unit
def test_cache_lookup_miss_goes_to_intent():
    """cache_hit=False이면 intent_router로 라우팅한다."""
    assert route_after_cache_lookup({"cache_hit": False}) == "intent_router"


@pytest.mark.unit
def test_cache_lookup_no_flag_goes_to_intent():
    """cache_hit가 없으면 intent_router로 라우팅한다."""
    assert route_after_cache_lookup({}) == "intent_router"


# ── route_after_intent_router ──

INTENT_MAPPING = [
    ("troubleshoot", "troubleshoot_agent"),
    ("install", "install_agent"),
    ("connect", "connect_agent"),
    ("clinical", "clinical_agent"),
    ("general", "placeholder_agent"),
]


@pytest.mark.unit
@pytest.mark.parametrize("intent, expected_node", INTENT_MAPPING)
def test_intent_router_all_intents(intent, expected_node):
    """각 의도가 올바른 에이전트 노드로 라우팅된다."""
    assert route_after_intent_router({"intent": intent}) == expected_node


@pytest.mark.unit
def test_intent_router_unknown_fallback():
    """알 수 없는 의도는 placeholder_agent로 폴백한다."""
    assert route_after_intent_router({"intent": "unknown"}) == "placeholder_agent"


@pytest.mark.unit
def test_intent_router_missing_intent():
    """intent가 없으면 기본값 general → placeholder_agent."""
    assert route_after_intent_router({}) == "placeholder_agent"


# ── route_after_guardrail ──


@pytest.mark.unit
def test_guardrail_passed_goes_to_cache_store():
    """guardrail_passed=True이면 cache_store로 라우팅한다."""
    assert route_after_guardrail({"guardrail_passed": True}) == "cache_store"


@pytest.mark.unit
def test_guardrail_failed_retry():
    """guardrail_passed=False, retry_count < MAX이면 fix_response로 라우팅한다."""
    state = {"guardrail_passed": False, "guardrail_retry_count": 0}
    assert route_after_guardrail(state) == "fix_response"


@pytest.mark.unit
def test_guardrail_failed_retry_boundary():
    """retry_count가 MAX-1이면 아직 fix_response로 라우팅한다."""
    state = {"guardrail_passed": False, "guardrail_retry_count": MAX_GUARDRAIL_RETRIES - 1}
    assert route_after_guardrail(state) == "fix_response"


@pytest.mark.unit
def test_guardrail_max_retry_goes_to_cache_store():
    """retry_count >= MAX이면 cache_store로 라우팅한다 (안전 폴백도 캐시)."""
    state = {"guardrail_passed": False, "guardrail_retry_count": MAX_GUARDRAIL_RETRIES}
    assert route_after_guardrail(state) == "cache_store"
