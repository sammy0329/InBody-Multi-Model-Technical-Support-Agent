"""연동 에이전트 노드 — T049, T050

기종별 주변기기 호환성 확인 및 연결 절차 안내.
호환되지 않는 주변기기에 대해 명확히 설명하고 대안을 제시한다.
"""

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config import settings
from src.models.inbody_models import get_model_profile
from src.models.state import AgentState
from src.prompts.system_prompts import CONNECT_AGENT_PROMPT
from src.prompts.tone_profiles import get_tone_instruction
from src.tools.manual_search_tool import extract_image_urls, search_manual
from src.tools.peripheral_tool import check_peripheral_compatibility

logger = logging.getLogger(__name__)

# 주변기기 유형 키워드 매핑
PERIPHERAL_TYPE_KEYWORDS: dict[str, list[str]] = {
    "printer": ["프린터", "인쇄", "출력", "결과지"],
    "pc": [
        "PC", "pc", "컴퓨터", "룩인바디", "LookInBody", "Lookin'Body",
        "EMR", "HIS", "소프트웨어", "LAN", "네트워크",
    ],
    "barcode_reader": ["바코드", "리더기", "스캐너"],
    "usb": ["USB", "usb", "메모리", "저장장치"],
}

# 주변기기 이름 키워드 (선택적 추출용)
PERIPHERAL_NAME_KEYWORDS: list[str] = [
    "Lookin'Body", "LookInBody", "룩인바디",
    "EMR", "HIS", "DICOM", "HL7",
]


async def connect_agent_node(state: AgentState) -> dict:
    """연동 에이전트: 주변기기 호환성 확인 + 연결 가이드 생성.

    흐름:
    1. 사용자 메시지에서 주변기기 유형/이름 키워드 추출
    2. check_peripheral_compatibility로 호환표 조회 (T049)
    3. search_manual로 연동 관련 매뉴얼 RAG 검색 (T049)
    4. 호환/비호환 여부에 따라 컨텍스트 구성 (T050)
    5. GPT-4o로 연결 가이드 생성
    """
    model_id = state["identified_model"]
    user_message = state["messages"][-1].content
    profile = get_model_profile(model_id)
    tone_instruction = get_tone_instruction(profile.tone_profile)

    # Step 1: 주변기기 유형/이름 키워드 추출
    peripheral_type = _extract_peripheral_type(user_message)
    peripheral_name = _extract_peripheral_name(user_message)

    # Step 2: 호환표 조회
    compat_result = await check_peripheral_compatibility.ainvoke({
        "model": model_id,
        "peripheral_type": peripheral_type,
        "peripheral_name": peripheral_name,
    })

    context_parts = [f"[주변기기 호환표 조회 결과]\n{compat_result}"]

    # Step 3: 매뉴얼 RAG 검색
    manual_result = search_manual.invoke({
        "model": model_id,
        "query": user_message,
    })
    context_parts.append(f"[연동 매뉴얼 검색 결과]\n{manual_result}")

    # T050: 비호환/미등록 감지 시 추가 컨텍스트 주입
    if "조건에 맞는 호환 정보가 없습니다" in compat_result:
        context_parts.append(
            "[비호환/미등록 주변기기 감지]\n"
            "요청한 주변기기가 호환표에 등록되어 있지 않습니다.\n"
            "가능하다면 해당 기종에서 지원하는 대체 주변기기를 안내하세요.\n"
            "공식 호환 목록에 없는 제품은 정상 동작을 보장할 수 없음을 안내하세요."
        )
    elif "비호환" in compat_result:
        context_parts.append(
            "[비호환 주변기기 감지]\n"
            "요청한 주변기기가 이 기종과 호환되지 않습니다.\n"
            "비호환 사유를 명확히 설명하고, 호환되는 대안을 제시하세요."
        )

    context = "\n\n".join(context_parts)

    # Step 4: GPT-4o로 응답 생성
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.3,
    )

    system_prompt = CONNECT_AGENT_PROMPT.format(
        model=model_id,
        tone_instruction=tone_instruction,
        context=context,
    )

    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ])

    return {
        "answer": response.content,
        "image_urls": extract_image_urls(manual_result),
    }


def _extract_peripheral_type(message: str) -> str:
    """사용자 메시지에서 주변기기 유형을 추출한다.

    PERIPHERAL_TYPE_KEYWORDS에서 첫 번째 매칭된 유형을 반환.
    매칭 없으면 빈 문자열 (전체 조회).
    """
    for ptype, keywords in PERIPHERAL_TYPE_KEYWORDS.items():
        if any(keyword in message for keyword in keywords):
            return ptype
    return ""


def _extract_peripheral_name(message: str) -> str:
    """사용자 메시지에서 주변기기 이름 키워드를 추출한다.

    PERIPHERAL_NAME_KEYWORDS에서 첫 번째 매칭된 키워드를 반환.
    매칭 없으면 빈 문자열.
    """
    for keyword in PERIPHERAL_NAME_KEYWORDS:
        if keyword.lower() in message.lower():
            return keyword
    return ""
