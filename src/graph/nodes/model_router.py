"""기종 식별 노드 (ModelRouter) — T031, T033, T034

GPT-4o-mini를 사용하여 사용자 메시지에서 InBody 기종을 식별한다.
3가지 분기: identified / unidentified / unsupported
"""

import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config import settings
from src.models.inbody_models import SUPPORTED_MODELS, get_model_profile
from src.models.state import AgentState
from src.prompts.disclaimers import SERVICE_CENTER_INFO
from src.prompts.system_prompts import MODEL_ROUTER_PROMPT

logger = logging.getLogger(__name__)


async def model_router_node(state: AgentState) -> dict:
    """사용자 메시지에서 InBody 기종을 식별한다.

    결과:
    - identified → identified_model, model_tier, tone_profile 설정
    - unidentified → answer에 기종 선택지 설정
    - unsupported → answer에 미지원 안내 설정
    """
    user_message = state["messages"][-1].content

    # 사전 검사: 메시지에 지원 기종명이 직접 포함된 경우 LLM 없이 즉시 식별
    pre_model = _pre_extract_model(user_message)
    if pre_model:
        profile = get_model_profile(pre_model)
        logger.info("사전 매칭으로 기종 식별: %s", pre_model)
        return {
            "identified_model": pre_model,
            "model_tier": profile.tier,
            "tone_profile": profile.tone_profile,
        }

    llm = ChatOpenAI(
        model=settings.openai_mini_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )

    response = await llm.ainvoke([
        SystemMessage(content=MODEL_ROUTER_PROMPT.format()),
        HumanMessage(content=user_message),
    ])

    # JSON 파싱
    try:
        result = json.loads(response.content.strip())
        model_id = result.get("model", "unidentified")
    except (json.JSONDecodeError, AttributeError):
        logger.warning("ModelRouter JSON 파싱 실패 — unidentified로 폴백")
        model_id = "unidentified"

    # identified: 지원 기종
    if model_id in SUPPORTED_MODELS:
        profile = get_model_profile(model_id)
        return {
            "identified_model": model_id,
            "model_tier": profile.tier,
            "tone_profile": profile.tone_profile,
        }

    # unsupported: 지원하지 않는 기종
    if model_id == "unsupported":
        return {
            "answer": (
                "죄송합니다. 현재 해당 기종은 지원 대상이 아닙니다.\n\n"
                f"현재 지원 기종: {', '.join(sorted(SUPPORTED_MODELS))}\n\n"
                "추가 도움이 필요하시면 InBody 공식 고객센터로 문의해 주세요.\n\n"
                f"{SERVICE_CENTER_INFO}"
            ),
        }

    # unidentified: 기종 미식별
    models_text = "\n".join(
        f"- **{mid}**: {get_model_profile(mid).description}"
        for mid in sorted(SUPPORTED_MODELS)
    )
    return {
        "answer": (
            "어떤 InBody 기종에 대해 도움이 필요하신가요? "
            "아래에서 사용 중인 기종을 선택해 주세요.\n\n"
            f"{models_text}"
        ),
    }


# 기종 패턴: "270S", "580", "770S", "970S" (대소문자 무시, 앞뒤 경계)
_MODEL_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(m) for m in sorted(SUPPORTED_MODELS)) + r")\b",
    re.IGNORECASE,
)


def _pre_extract_model(message: str) -> str | None:
    """메시지에서 지원 기종명을 직접 매칭한다.

    정규식으로 270S/580/770S/970S를 탐지.
    매칭되면 기종 ID(대문자) 반환, 없으면 None.
    """
    match = _MODEL_PATTERN.search(message)
    if match:
        return match.group(1).upper()
    return None
