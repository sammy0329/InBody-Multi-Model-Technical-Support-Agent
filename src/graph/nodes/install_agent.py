"""설치 도우미 에이전트 노드 — T046, T047

기종별 설치 유형(접이식/분리형)에 맞는 단계별 설치 안내.
설치 중 문제 발생 시 해당 단계 체크리스트를 제시한다.
"""

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config import settings
from src.models.inbody_models import get_model_profile
from src.models.state import AgentState
from src.prompts.system_prompts import INSTALL_AGENT_PROMPT
from src.prompts.tone_profiles import get_tone_instruction
from src.tools.manual_search_tool import extract_image_urls, search_manual

logger = logging.getLogger(__name__)

INSTALL_TYPE_LABELS = {
    "foldable": "접이식",
    "separable": "분리형",
}

# 설치 중 문제 감지 키워드 (T047)
INSTALL_TROUBLE_KEYWORDS = [
    "안 켜", "안켜", "켜지지 않", "전원이 안",
    "안 되", "안되", "안 돼", "안돼",
    "조립이", "연결이", "끼워지지", "맞지 않",
    "빠져", "헐거", "단단하지",
    "화면이 안", "부팅이 안", "소리가",
]


async def install_agent_node(state: AgentState) -> dict:
    """설치 도우미 에이전트: 기종별 설치 가이드 생성.

    흐름:
    1. 기종의 설치 유형(접이식/분리형) 확인 (T046)
    2. search_manual로 설치 매뉴얼 RAG 검색 (T046)
    3. 설치 중 문제 감지 시 체크리스트 컨텍스트 추가 (T047)
    4. GPT-4o로 단계별 설치 가이드 생성
    """
    model_id = state["identified_model"]
    user_message = state["messages"][-1].content
    profile = get_model_profile(model_id)
    tone_instruction = get_tone_instruction(profile.tone_profile)
    install_type = profile.install_type

    # Step 1: 설치 매뉴얼 RAG 검색
    manual_result = search_manual.invoke({
        "model": model_id,
        "query": user_message,
    })

    context_parts = [f"[설치 매뉴얼 검색 결과]\n{manual_result}"]

    # Step 2: 설치 유형 정보 추가
    install_label = INSTALL_TYPE_LABELS.get(install_type, install_type)
    context_parts.append(
        f"[설치 유형 정보]\n"
        f"이 기종은 {install_label} 설치 유형입니다.\n"
        f"- 접이식(foldable): 본체를 펼쳐서 설치하는 방식 (270S, 580)\n"
        f"- 분리형(separable): 본체와 전극부를 분리 조립하는 방식 (770S, 970S)"
    )

    # T047: 설치 중 문제 감지
    if _is_install_trouble(user_message):
        context_parts.append(
            "[설치 중 문제 감지]\n"
            "사용자가 설치 과정에서 특정 단계에 막혀 있습니다.\n"
            "해당 단계에 대한 체크리스트를 제시하세요:\n"
            "- 해당 단계의 전제 조건이 충족되었는지 확인\n"
            "- 일반적인 실수나 누락 사항 안내\n"
            "- 물리적 연결 상태(케이블, 커넥터, 나사 등) 점검 항목\n"
            "- 그래도 해결되지 않을 경우 서비스 센터 연락 안내"
        )

    context = "\n\n".join(context_parts)

    # Step 3: GPT-4o로 응답 생성
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.3,
    )

    system_prompt = INSTALL_AGENT_PROMPT.format(
        model=model_id,
        tone_instruction=tone_instruction,
        install_type=install_label,
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


def _is_install_trouble(message: str) -> bool:
    """설치 중 문제 키워드를 감지한다."""
    return any(keyword in message for keyword in INSTALL_TROUBLE_KEYWORDS)
