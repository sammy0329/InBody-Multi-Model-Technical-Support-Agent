"""시멘틱 캐시 LangGraph 노드 — T116, T117

cache_lookup: ModelRouter 이후 캐시 조회, 히트 시 answer 설정
cache_store: Guardrail 통과 후 응답을 캐시에 저장
"""

import logging

from src.cache.semantic_cache import get_semantic_cache
from src.config import settings
from src.models.state import AgentState

logger = logging.getLogger(__name__)


async def cache_lookup_node(state: AgentState) -> dict:
    """캐시 조회 노드 (T116).

    ModelRouter 이후, IntentRouter 이전에 실행된다.
    캐시 히트 시 answer를 설정하고 cache_hit=True로 표시하여
    이후 워크플로우(IntentRouter → Agent → Guardrail)를 건너뛴다.
    """
    if not settings.enable_semantic_cache:
        return {"cache_hit": False, "cache_key": None}

    identified_model = state.get("identified_model")
    if not identified_model:
        return {"cache_hit": False, "cache_key": None}

    messages = state.get("messages", [])
    if not messages:
        return {"cache_hit": False, "cache_key": None}

    user_query = messages[-1].content

    cache = get_semantic_cache()
    entry = cache.lookup(query=user_query, model_id=identified_model)

    if entry is None:
        logger.debug("캐시 미스: model=%s", identified_model)
        return {"cache_hit": False, "cache_key": None}

    logger.info(
        "캐시 히트: model=%s, intent=%s, similarity=%.3f",
        identified_model, entry.intent, entry.similarity,
    )
    return {
        "cache_hit": True,
        "cache_key": entry.cache_id,
        "answer": entry.response,
        "intent": entry.intent,
        "support_level": entry.support_level or None,
        "needs_disclaimer": entry.disclaimer_included,
        "image_urls": entry.image_urls,
        "guardrail_passed": True,
    }


async def cache_store_node(state: AgentState) -> dict:
    """캐시 저장 노드 (T117).

    Guardrail 통과 후 응답을 캐시에 저장한다.
    guardrail_passed=True인 응답만 저장하며, 캐시 히트 응답은 재저장하지 않는다.
    """
    if not settings.enable_semantic_cache:
        return {}

    # 캐시 히트 응답은 재저장하지 않음
    if state.get("cache_hit"):
        return {}

    if not state.get("guardrail_passed"):
        return {}

    identified_model = state.get("identified_model")
    intent = state.get("intent")
    answer = state.get("answer")

    if not identified_model or not intent or not answer:
        return {}

    messages = state.get("messages", [])
    if not messages:
        return {}

    # 사용자의 원래 질문 추출 (마지막 HumanMessage)
    user_query = None
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "human":
            user_query = msg.content
            break
        if hasattr(msg, "role") and msg.role == "user":
            user_query = msg.content
            break

    if not user_query:
        return {}

    cache = get_semantic_cache()
    cache_id = cache.store(
        query=user_query,
        model_id=identified_model,
        intent=intent,
        response=answer,
        support_level=state.get("support_level"),
        disclaimer_included=state.get("needs_disclaimer", False),
        image_urls=state.get("image_urls", []),
        guardrail_passed=True,
    )

    if cache_id:
        logger.info("캐시 저장 완료: model=%s, intent=%s, id=%s", identified_model, intent, cache_id)

    return {}
