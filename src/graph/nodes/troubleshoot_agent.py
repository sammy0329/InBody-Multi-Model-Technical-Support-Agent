"""트러블슈팅 에이전트 노드 — T040, T041, T042, T043

에러 코드 분석 및 단계별 해결책 제시.
Level 1(사용자 해결)과 Level 3(서비스 센터 이관)을 엄격히 구분한다.
"""

import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config import settings
from src.models.inbody_models import get_model_profile
from src.models.state import AgentState
from src.prompts.disclaimers import HARDWARE_DISCLAIMER, SERVICE_CENTER_INFO
from src.prompts.system_prompts import TROUBLESHOOT_AGENT_PROMPT
from src.prompts.tone_profiles import get_tone_instruction
from src.tools.error_code_tool import lookup_error_code, search_errors_by_symptom
from src.tools.manual_search_tool import search_manual

logger = logging.getLogger(__name__)

# 에스컬레이션 감지 키워드 (T043)
ESCALATION_KEYWORDS = [
    "안 돼", "안돼", "해결되지 않", "해결 안", "해결안",
    "여전히", "안됐", "안되", "또 나", "다시 나",
    "계속", "같은 문제", "동일한 문제",
]


async def troubleshoot_agent_node(state: AgentState) -> dict:
    """트러블슈팅 에이전트: 에러 코드 분석 + 해결책 생성.

    흐름:
    1. 사용자 메시지에서 에러 코드 추출 (T040)
    2. 에러 코드 있음 → lookup_error_code 호출
       에러 코드 없음 → search_errors_by_symptom + search_manual RAG 검색 (T041)
    3. Level 1/Level 3 분기 응답 생성 (T042)
    4. 에스컬레이션 감지 시 Level 3 이관 안내 (T043)
    """
    model_id = state["identified_model"]
    user_message = state["messages"][-1].content
    profile = get_model_profile(model_id)
    tone_instruction = get_tone_instruction(profile.tone_profile)

    # Step 1: 에러 코드 추출
    error_code = _extract_error_code(user_message)
    is_escalation = _is_escalation(user_message)

    # Step 2: 도구 호출로 컨텍스트 수집
    context_parts = []
    support_level = None

    if error_code:
        # T040: 에러 코드 조회
        error_result = await lookup_error_code.ainvoke({
            "model": model_id,
            "error_code": error_code,
        })
        context_parts.append(f"[에러 코드 조회 결과]\n{error_result}")

        # support_level 추출
        if "서비스 센터 이관 필요 (Level 3)" in error_result:
            support_level = "level_3"
        elif "사용자 해결 가능 (Level 1)" in error_result:
            support_level = "level_1"
    else:
        # T041: 증상 기반 검색
        symptom_result = await search_errors_by_symptom.ainvoke({
            "model": model_id,
            "symptom_description": user_message,
        })
        context_parts.append(f"[증상 기반 에러 검색 결과]\n{symptom_result}")

        # 매뉴얼 RAG 검색
        manual_result = search_manual.invoke({
            "model": model_id,
            "query": user_message,
            "category": "troubleshooting",
        })
        context_parts.append(f"[매뉴얼 검색 결과]\n{manual_result}")

    # T043: 에스컬레이션 감지
    if is_escalation:
        context_parts.append(
            "[에스컬레이션 감지]\n"
            "사용자가 이전 해결 방법으로 문제가 해결되지 않았다고 보고했습니다.\n"
            "다음 단계의 해결책을 제시하거나, 더 이상 사용자 해결이 불가능하면 "
            "서비스 센터(Level 3) 이관을 안내하세요."
        )

    context = "\n\n".join(context_parts)

    # Step 3: GPT-4o로 응답 생성
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.3,
    )

    system_prompt = TROUBLESHOOT_AGENT_PROMPT.format(
        model=model_id,
        tone_instruction=tone_instruction,
        context=context,
    )

    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ])

    answer = response.content

    # T042: Level 3 → 하드웨어 면책 + 서비스 센터 정보 추가
    if support_level == "level_3":
        answer += f"\n\n{HARDWARE_DISCLAIMER}\n\n{SERVICE_CENTER_INFO}"

    # T043: 에스컬레이션 + Level 1 → 서비스 센터 안내 추가
    if is_escalation and support_level == "level_1":
        answer += (
            "\n\n위 방법으로도 해결되지 않으시면 "
            "InBody 서비스 센터로 문의해 주세요.\n\n"
            f"{SERVICE_CENTER_INFO}"
        )

    return {
        "answer": answer,
        "error_code": error_code,
        "support_level": support_level,
    }


def _extract_error_code(message: str) -> str | None:
    """사용자 메시지에서 에러 코드를 추출한다.

    지원 형식: E001, e001, 에러코드 E001, 에러 001, 오류코드 E001
    """
    # Pattern 1: E + 3자리 숫자 (가장 일반적)
    match = re.search(r'[Ee](\d{3})', message)
    if match:
        return f"E{match.group(1)}"

    # Pattern 2: 에러/오류 키워드 + 숫자
    match = re.search(r'(?:에러|오류)\s*(?:코드)?\s*(\d{3})', message)
    if match:
        return f"E{match.group(1)}"

    return None


def _is_escalation(message: str) -> bool:
    """에스컬레이션 키워드를 감지한다."""
    return any(keyword in message for keyword in ESCALATION_KEYWORDS)
