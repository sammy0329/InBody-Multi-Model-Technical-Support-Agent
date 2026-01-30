"""기종 식별 노드 (ModelRouter) — T031, T033, T034, T063, T064

GPT-4o-mini를 사용하여 사용자 메시지에서 InBody 기종을 식별한다.
분기: identified / unidentified / unsupported / comparison / model_change
"""

import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config import settings
from src.models.inbody_models import INBODY_MODELS, SUPPORTED_MODELS, get_model_profile
from src.models.state import AgentState
from src.prompts.disclaimers import SERVICE_CENTER_INFO
from src.prompts.system_prompts import MODEL_ROUTER_PROMPT

logger = logging.getLogger(__name__)


async def model_router_node(state: AgentState) -> dict:
    """사용자 메시지에서 InBody 기종을 식별한다.

    결과:
    - comparison → answer에 비교 정보 설정 (T064)
    - identified → identified_model, model_tier, tone_profile 설정
    - model_change → 기종 변경 감지 후 새 기종으로 설정 (T063)
    - unidentified (이전 기종 있음) → 이전 기종 유지 (T063)
    - unidentified (이전 기종 없음) → answer에 기종 선택지 설정
    - unsupported → answer에 미지원 안내 설정
    """
    user_message = state["messages"][-1].content
    previous_model = state.get("identified_model")

    # ── T064: 복수 기종 감지 (비교 질문) ──
    all_models = _extract_all_models(user_message)
    if len(all_models) >= 2:
        logger.info("기종 비교 질문 감지: %s", all_models)
        return {"answer": _build_comparison_response(all_models)}

    # ── 사전 검사: 메시지에 지원 기종명이 직접 포함된 경우 LLM 없이 즉시 식별
    pre_model = _pre_extract_model(user_message)
    if pre_model:
        profile = get_model_profile(pre_model)
        logger.info("사전 매칭으로 기종 식별: %s", pre_model)
        # T063: 기종 변경 감지
        if previous_model and previous_model != pre_model:
            logger.info("기종 변경 감지: %s → %s", previous_model, pre_model)
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
        # T063: 기종 변경 감지
        if previous_model and previous_model != model_id:
            logger.info("기종 변경 감지: %s → %s", previous_model, model_id)
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

    # T063: unidentified이지만 이전 기종이 있으면 유지
    if previous_model:
        logger.info("기종 미식별 — 이전 기종 %s 유지", previous_model)
        return {}

    # unidentified: 기종 미식별 (첫 턴)
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


# 기종 패턴: "270S", "580", "770S", "970S" (대소문자 무시, ASCII 경계)
# \b 대신 ASCII 경계 사용 — 한국어 유니코드 문자가 \w에 포함되어
# "270S와" 같은 표현에서 \b가 매칭 실패하는 문제 방지
_MODEL_PATTERN = re.compile(
    r"(?<![a-zA-Z0-9])("
    + "|".join(re.escape(m) for m in sorted(SUPPORTED_MODELS))
    + r")(?![a-zA-Z0-9])",
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


def _extract_all_models(message: str) -> list[str]:
    """메시지에서 모든 지원 기종명을 추출한다 (T064).

    "270S와 580 차이" → ["270S", "580"]
    중복 제거, 순서 유지.
    """
    matches = _MODEL_PATTERN.findall(message)
    seen: set[str] = set()
    result: list[str] = []
    for m in matches:
        upper = m.upper()
        if upper not in seen:
            seen.add(upper)
            result.append(upper)
    return result


def _build_comparison_response(models: list[str]) -> str:
    """복수 기종 비교 응답을 생성한다 (T064)."""
    lines = [f"요청하신 {', '.join(models)} 기종의 비교 정보입니다.\n"]

    for model_id in models:
        profile = INBODY_MODELS[model_id]
        tier_label = "보급형" if profile.tier == "entry" else "전문가용"
        install_label = "접이식" if profile.install_type == "foldable" else "분리형"
        lines.append(
            f"### {profile.name}\n"
            f"- **분류**: {tier_label}\n"
            f"- **설치 유형**: {install_label}\n"
            f"- **측정 항목**: {', '.join(profile.measurement_items)}\n"
            f"- **설명**: {profile.description}\n"
        )

    lines.append(
        "자세한 비교가 필요하시면 특정 항목(설치, 측정, 연동 등)을 알려주세요."
    )

    return "\n".join(lines)
