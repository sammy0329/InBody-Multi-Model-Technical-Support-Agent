"""의도 분류 노드 (IntentRouter) — T035

GPT-4o-mini를 사용하여 사용자 메시지의 의도를 5가지 중 하나로 분류한다.
install / connect / troubleshoot / clinical / general
"""

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config import settings
from src.models.state import AgentState
from src.prompts.system_prompts import INTENT_ROUTER_PROMPT

logger = logging.getLogger(__name__)

VALID_INTENTS = {"install", "connect", "troubleshoot", "clinical", "general"}


async def intent_router_node(state: AgentState) -> dict:
    """사용자 메시지의 의도를 분류한다.

    5가지 의도: install, connect, troubleshoot, clinical, general
    clinical이면 needs_disclaimer=True 설정
    """
    user_message = state["messages"][-1].content

    llm = ChatOpenAI(
        model=settings.openai_mini_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )

    response = await llm.ainvoke([
        SystemMessage(content=INTENT_ROUTER_PROMPT.format()),
        HumanMessage(content=user_message),
    ])

    try:
        result = json.loads(response.content.strip())
        intent = result.get("intent", "general")
        if intent not in VALID_INTENTS:
            intent = "general"
    except (json.JSONDecodeError, AttributeError):
        logger.warning("IntentRouter JSON 파싱 실패 — general로 폴백")
        intent = "general"

    return {
        "intent": intent,
        "needs_disclaimer": intent == "clinical",
    }
