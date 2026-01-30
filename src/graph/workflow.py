"""LangGraph 워크플로우 정의 — T029, T045, T048, T052, T055, T057, T058, T062

START → model_router → [조건부 엣지]
                          ├── identified → intent_router → [조건부 엣지]
                          │                                  ├── troubleshoot → troubleshoot_agent ─┐
                          │                                  ├── install → install_agent ────────────┤
                          │                                  ├── connect → connect_agent ────────────┤
                          │                                  ├── clinical → clinical_agent ──────────┤
                          │                                  └── 그 외 → placeholder_agent ──────────┤
                          │                                                                         ▼
                          │                                                                    guardrail
                          │                                                                    ├── 통과 → END
                          │                                                                    └── 실패 → fix_response → guardrail (최대 2회)
                          └── unidentified/unsupported → END (answer 이미 설정됨)
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.graph.edges import (
    route_after_guardrail,
    route_after_intent_router,
    route_after_model_router,
)
from src.graph.nodes.clinical_agent import clinical_agent_node
from src.graph.nodes.connect_agent import connect_agent_node
from src.graph.nodes.guardrail import fix_response_node, guardrail_node
from src.graph.nodes.install_agent import install_agent_node
from src.graph.nodes.intent_router import intent_router_node
from src.graph.nodes.model_router import model_router_node
from src.graph.nodes.placeholder_agent import placeholder_agent_node
from src.graph.nodes.troubleshoot_agent import troubleshoot_agent_node
from src.models.state import AgentState

# 체크포인터 싱글톤 (T062)
_checkpointer: MemorySaver | None = None


def get_checkpointer() -> MemorySaver:
    """InMemorySaver 체크포인터 싱글톤을 반환한다."""
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = MemorySaver()
    return _checkpointer


def create_workflow() -> StateGraph:
    """LangGraph StateGraph를 생성한다."""
    workflow = StateGraph(AgentState)

    # 노드 등록
    workflow.add_node("model_router", model_router_node)
    workflow.add_node("intent_router", intent_router_node)
    workflow.add_node("placeholder_agent", placeholder_agent_node)
    workflow.add_node("troubleshoot_agent", troubleshoot_agent_node)
    workflow.add_node("install_agent", install_agent_node)
    workflow.add_node("connect_agent", connect_agent_node)
    workflow.add_node("clinical_agent", clinical_agent_node)
    workflow.add_node("guardrail", guardrail_node)
    workflow.add_node("fix_response", fix_response_node)

    # 엣지 설정
    workflow.set_entry_point("model_router")

    workflow.add_conditional_edges(
        "model_router",
        route_after_model_router,
        {"intent_router": "intent_router", "__end__": END},
    )

    workflow.add_conditional_edges(
        "intent_router",
        route_after_intent_router,
        {
            "troubleshoot_agent": "troubleshoot_agent",
            "install_agent": "install_agent",
            "connect_agent": "connect_agent",
            "clinical_agent": "clinical_agent",
            "placeholder_agent": "placeholder_agent",
        },
    )

    # 모든 에이전트 → guardrail
    workflow.add_edge("troubleshoot_agent", "guardrail")
    workflow.add_edge("install_agent", "guardrail")
    workflow.add_edge("connect_agent", "guardrail")
    workflow.add_edge("clinical_agent", "guardrail")
    workflow.add_edge("placeholder_agent", "guardrail")

    # guardrail → 조건부 엣지 (통과/실패)
    workflow.add_conditional_edges(
        "guardrail",
        route_after_guardrail,
        {"__end__": END, "fix_response": "fix_response"},
    )

    # fix_response → guardrail (재검증 루프)
    workflow.add_edge("fix_response", "guardrail")

    return workflow


def get_compiled_workflow():
    """체크포인터가 연결된 컴파일된 워크플로우를 반환한다."""
    checkpointer = get_checkpointer()
    return create_workflow().compile(checkpointer=checkpointer)
