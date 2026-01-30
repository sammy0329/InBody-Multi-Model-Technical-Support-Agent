"""임상 방어 에이전트 노드 — T053, T054

측정 결과 신뢰성 방어 및 생리학적 변수 설명.
의학적 진단 요청을 감지하여 거절하고, 모든 응답에 MEDICAL_DISCLAIMER를 필수 포함한다.
"""

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config import settings
from src.models.inbody_models import get_model_profile
from src.models.state import AgentState
from src.prompts.disclaimers import MEDICAL_DISCLAIMER
from src.prompts.system_prompts import CLINICAL_AGENT_PROMPT
from src.prompts.tone_profiles import get_tone_instruction
from src.tools.manual_search_tool import extract_image_urls, search_manual

logger = logging.getLogger(__name__)

# T054: 의학적 진단 요청 감지 키워드
DIAGNOSIS_KEYWORDS: list[str] = [
    "진단", "질환", "질병", "병", "증상",
    "치료", "약", "처방", "수술",
    "당뇨", "고혈압", "암", "심장", "간",
    "신장", "갑상선", "빈혈",
]


async def clinical_agent_node(state: AgentState) -> dict:
    """임상 방어 에이전트: 측정 결과 해석 + 면책 문구 필수 포함.

    흐름:
    1. 기종 프로필에서 measurement_items 추출
    2. search_manual로 측정 관련 매뉴얼 RAG 검색
    3. 의학적 진단 요청 키워드 감지 (T054)
    4. CLINICAL_AGENT_PROMPT + GPT-4o로 응답 생성
    5. 응답 끝에 MEDICAL_DISCLAIMER 필수 추가
    """
    model_id = state["identified_model"]
    user_message = state["messages"][-1].content
    profile = get_model_profile(model_id)
    tone_instruction = get_tone_instruction(profile.tone_profile)

    # Step 1: 측정 항목 추출
    measurement_items = ", ".join(profile.measurement_items)

    # Step 2: 매뉴얼 RAG 검색
    manual_result = search_manual.invoke({
        "model": model_id,
        "query": user_message,
    })
    context_parts = [f"[매뉴얼 검색 결과]\n{manual_result}"]

    # Step 3: T054 — 의학적 진단 요청 감지
    if _detect_diagnosis_request(user_message):
        context_parts.append(
            "[의학적 진단 요청 감지]\n"
            "사용자가 특정 질환에 대한 진단 또는 의학적 판단을 요청하고 있습니다.\n"
            "InBody는 체성분 분석 장비이며, 의학적 진단 도구가 아닙니다.\n"
            "진단은 절대 불가함을 명확히 안내하고, 전문 의료인 상담을 권고하세요."
        )

    context = "\n\n".join(context_parts)

    # Step 4: GPT-4o로 응답 생성
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.3,
    )

    system_prompt = CLINICAL_AGENT_PROMPT.format(
        model=model_id,
        tone_instruction=tone_instruction,
        measurement_items=measurement_items,
        context=context,
    )

    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ])

    # Step 5: MEDICAL_DISCLAIMER 강제 추가 (이중 보장)
    answer = response.content
    if MEDICAL_DISCLAIMER not in answer:
        answer = f"{answer}\n\n{MEDICAL_DISCLAIMER}"

    return {
        "answer": answer,
        "needs_disclaimer": True,
        "image_urls": extract_image_urls(manual_result),
    }


def _detect_diagnosis_request(message: str) -> bool:
    """사용자 메시지에서 의학적 진단 요청 키워드를 감지한다.

    DIAGNOSIS_KEYWORDS 중 하나라도 포함되면 True.
    """
    return any(keyword in message for keyword in DIAGNOSIS_KEYWORDS)
