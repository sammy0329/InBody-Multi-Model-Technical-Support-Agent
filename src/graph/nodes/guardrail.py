"""가드레일 안전 검증 노드 — T056, T058

모든 에이전트 출력을 검증하고 안전 위반 시 수정한다.
결정론적 검사(면책 문구, 기종 격리, Level 3 안전) 우선,
LLM 검증(GPT-4o-mini)은 보조적으로 사용한다.
"""

import json
import logging
import re

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

from src.config import settings
from src.models.inbody_models import SUPPORTED_MODELS
from src.models.state import AgentState
from src.prompts.disclaimers import (
    HARDWARE_DISCLAIMER,
    MEDICAL_DISCLAIMER,
    SERVICE_CENTER_INFO,
)
from src.prompts.system_prompts import GUARDRAIL_PROMPT

logger = logging.getLogger(__name__)

MAX_GUARDRAIL_RETRIES = 2

# Level 3 안전 위반 감지 키워드 — 사용자 직접 수리 유도 표현
UNSAFE_REPAIR_KEYWORDS: list[str] = [
    "내부 부품", "메인보드", "센서 교체", "분해",
    "하우징 열", "직접 수리", "내부를 열", "커버를 분리",
]


async def guardrail_node(state: AgentState) -> dict:
    """가드레일 안전 검증 노드.

    검사 순서:
    1. 면책 문구 검증 (결정론적, 자동 삽입)
    2. 기종 격리 검증 (결정론적, hard-fail)
    3. Level 3 안전 검증 (결정론적, hard-fail)
    4. LLM 종합 검증 (GPT-4o-mini, hard-fail 없을 때만)
    """
    answer = state.get("answer", "")
    identified_model = state.get("identified_model")
    intent = state.get("intent", "general")
    retry_count = state.get("guardrail_retry_count", 0)

    if not answer:
        return {
            "guardrail_passed": True,
            "guardrail_violations": [],
            "guardrail_suggestion": None,
        }

    violations: list[str] = []
    hard_fail = False

    # ── 검사 1: 면책 문구 검증 (자동 삽입) ──
    if state.get("needs_disclaimer") and MEDICAL_DISCLAIMER not in answer:
        answer = f"{answer}\n\n{MEDICAL_DISCLAIMER}"
        violations.append("면책 문구 자동 삽입: MEDICAL_DISCLAIMER 누락")

    if state.get("support_level") == "level_3" and HARDWARE_DISCLAIMER not in answer:
        answer = f"{answer}\n\n{HARDWARE_DISCLAIMER}"
        violations.append("면책 문구 자동 삽입: HARDWARE_DISCLAIMER 누락 (Level 3)")

    # ── 검사 2: 기종 격리 검증 (hard-fail) ──
    if identified_model:
        other_models = SUPPORTED_MODELS - {identified_model}
        for other_model in other_models:
            pattern = rf"\bInBody\s+{re.escape(other_model)}\b"
            if re.search(pattern, answer, re.IGNORECASE):
                violations.append(
                    f"기종 격리 위반: {other_model} 기종 정보가 응답에 포함됨"
                )
                hard_fail = True

    # ── 검사 3: Level 3 안전 검증 (hard-fail) ──
    if state.get("support_level") == "level_3":
        for keyword in UNSAFE_REPAIR_KEYWORDS:
            if keyword in answer:
                violations.append(
                    f"Level 3 안전 위반: '{keyword}' — 사용자 직접 수리 안내 감지"
                )
                hard_fail = True
                break

    # ── 검사 4: LLM 종합 검증 (hard-fail 없을 때만) ──
    suggestion = None
    if not hard_fail and identified_model:
        try:
            llm = ChatOpenAI(
                model=settings.openai_mini_model,
                api_key=settings.openai_api_key,
                temperature=0,
            )
            guardrail_prompt = GUARDRAIL_PROMPT.format(
                model=identified_model,
                intent=intent,
                answer=answer,
            )
            response = await llm.ainvoke([SystemMessage(content=guardrail_prompt)])
            result = json.loads(response.content.strip())

            if not result.get("passed", True):
                llm_violations = result.get("violations", [])
                violations.extend(llm_violations)
                suggestion = result.get("suggestion", "")
                hard_fail = True
        except (json.JSONDecodeError, Exception):
            logger.warning("가드레일 LLM 검증 실패 — 통과 처리")

    # ── 최대 재시도 초과 시 안전 폴백 ──
    if hard_fail and retry_count >= MAX_GUARDRAIL_RETRIES:
        logger.warning("가드레일 최대 재시도 초과 — 안전 폴백 메시지 반환")
        answer = (
            "죄송합니다. 안전한 응답을 생성하지 못했습니다. "
            f"InBody 고객센터로 직접 문의해 주세요.\n\n{SERVICE_CENTER_INFO}"
        )
        return {
            "answer": answer,
            "guardrail_passed": True,
            "guardrail_violations": violations,
            "guardrail_suggestion": None,
        }

    return {
        "answer": answer,
        "guardrail_passed": not hard_fail,
        "guardrail_violations": violations,
        "guardrail_suggestion": suggestion,
    }


async def fix_response_node(state: AgentState) -> dict:
    """가드레일 위반 시 응답을 수정한다.

    guardrail_violations와 guardrail_suggestion을 기반으로
    GPT-4o가 수정된 응답을 생성한다.
    """
    identified_model = state.get("identified_model", "알 수 없음")
    violations = state.get("guardrail_violations", [])
    suggestion = state.get("guardrail_suggestion", "")
    original_answer = state.get("answer", "")
    retry_count = state.get("guardrail_retry_count", 0)

    fix_prompt = (
        f"다음 InBody {identified_model} 기술 지원 응답에서 안전 위반이 감지되었습니다.\n\n"
        f"원래 응답:\n{original_answer}\n\n"
        f"위반 사항:\n" + "\n".join(f"- {v}" for v in violations) + "\n\n"
        f"수정 제안: {suggestion}\n\n"
        f"위 위반 사항을 모두 수정한 응답을 작성하세요. "
        f"반드시 {identified_model} 기종에 대한 정보만 포함하세요."
    )

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
    )

    response = await llm.ainvoke([SystemMessage(content=fix_prompt)])

    return {
        "answer": response.content,
        "guardrail_retry_count": retry_count + 1,
        "guardrail_passed": None,
        "guardrail_violations": [],
        "guardrail_suggestion": None,
    }
