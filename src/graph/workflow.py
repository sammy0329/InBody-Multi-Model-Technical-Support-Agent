"""LangGraph 워크플로우 정의 — T029

START → model_router → [조건부 엣지]
                          ├── identified → intent_router → placeholder_agent → END
                          └── unidentified/unsupported → END (answer 이미 설정됨)
"""

from langgraph.graph import END, StateGraph

from src.graph.edges import route_after_intent_router, route_after_model_router
from src.graph.nodes.intent_router import intent_router_node
from src.graph.nodes.model_router import model_router_node
from src.graph.nodes.placeholder_agent import placeholder_agent_node
from src.models.state import AgentState


def create_workflow() -> StateGraph:
    """LangGraph StateGraph를 생성한다."""
    workflow = StateGraph(AgentState)

    # 노드 등록
    workflow.add_node("model_router", model_router_node)
    workflow.add_node("intent_router", intent_router_node)
    workflow.add_node("placeholder_agent", placeholder_agent_node)

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
        {"placeholder_agent": "placeholder_agent"},
    )

    workflow.add_edge("placeholder_agent", END)

    return workflow


def get_compiled_workflow():
    """컴파일된 워크플로우를 반환한다."""
    return create_workflow().compile()
