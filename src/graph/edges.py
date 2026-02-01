"""조건부 엣지 라우팅 함수 — T030, T036, T055, T057, T064, T119"""

from src.models.state import AgentState


def route_after_model_router(state: AgentState) -> str:
    """ModelRouter 결과에 따라 다음 노드를 결정한다.

    - answer가 설정됨 (비교/unsupported/unidentified) → END (T064)
    - identified_model이 설정됨 → cache_lookup으로 진행 (T119)
    - 그 외 → END
    """
    if state.get("answer"):
        return "__end__"
    if state.get("identified_model"):
        return "cache_lookup"
    return "__end__"


def route_after_cache_lookup(state: AgentState) -> str:
    """CacheLookup 결과에 따라 다음 노드를 결정한다 (T119).

    - cache_hit=True → END (캐시된 응답 사용)
    - cache_hit=False → intent_router로 진행
    """
    if state.get("cache_hit"):
        return "__end__"
    return "intent_router"


def route_after_intent_router(state: AgentState) -> str:
    """IntentRouter 결과에 따라 다음 노드를 결정한다.

    - troubleshoot → troubleshoot_agent (Phase 4)
    - install → install_agent (Phase 5)
    - connect → connect_agent (Phase 6)
    - clinical → clinical_agent (Phase 7)
    - 그 외 → placeholder_agent (Phase 8 이후 확장 예정)
    """
    intent = state.get("intent", "general")
    if intent == "troubleshoot":
        return "troubleshoot_agent"
    if intent == "install":
        return "install_agent"
    if intent == "connect":
        return "connect_agent"
    if intent == "clinical":
        return "clinical_agent"
    return "placeholder_agent"


MAX_GUARDRAIL_RETRIES = 2


def route_after_guardrail(state: AgentState) -> str:
    """Guardrail 결과에 따라 다음 노드를 결정한다.

    - guardrail_passed=True → cache_store (T118)
    - guardrail_passed=False, 재시도 가능 → fix_response
    - guardrail_passed=False, 최대 재시도 초과 → cache_store (안전 폴백도 캐시)
    """
    if state.get("guardrail_passed"):
        return "cache_store"
    if state.get("guardrail_retry_count", 0) < MAX_GUARDRAIL_RETRIES:
        return "fix_response"
    return "cache_store"
