"""조건부 엣지 라우팅 함수 — T030, T036"""

from src.models.state import AgentState


def route_after_model_router(state: AgentState) -> str:
    """ModelRouter 결과에 따라 다음 노드를 결정한다.

    - identified_model이 설정됨 → intent_router로 진행
    - answer가 설정됨 (unidentified/unsupported) → END
    """
    if state.get("identified_model"):
        return "intent_router"
    return "__end__"


def route_after_intent_router(state: AgentState) -> str:
    """IntentRouter 결과에 따라 다음 노드를 결정한다.

    - troubleshoot → troubleshoot_agent (Phase 4)
    - install → install_agent (Phase 5)
    - 그 외 → placeholder_agent (Phase 6~7에서 전문 에이전트로 대체 예정)
    """
    intent = state.get("intent", "general")
    if intent == "troubleshoot":
        return "troubleshoot_agent"
    if intent == "install":
        return "install_agent"
    return "placeholder_agent"
