"""임시 응답 에이전트 (Phase 3)

Phase 4~7에서 전문 에이전트(install, connect, troubleshoot, clinical)로 대체 예정.
기종/의도 식별 후 톤앤매너를 적용한 임시 응답을 생성한다.
외부 의존성 없음 (순수 상태 조작).
"""

from src.models.inbody_models import get_model_profile
from src.models.state import AgentState
from src.prompts.disclaimers import MEDICAL_DISCLAIMER

INTENT_LABELS = {
    "install": "설치",
    "connect": "연동",
    "troubleshoot": "트러블슈팅",
    "clinical": "임상 해석",
    "general": "일반",
}


async def placeholder_agent_node(state: AgentState) -> dict:
    """기종과 의도가 식별된 후 임시 응답을 생성한다."""
    model_id = state["identified_model"]
    intent = state.get("intent", "general")
    profile = get_model_profile(model_id)

    intent_label = INTENT_LABELS.get(intent, "일반")
    tone_desc = "친근한 보급형" if profile.tone_profile == "casual" else "전문가용"

    answer = (
        f"안녕하세요! InBody {model_id} {intent_label} 관련 문의를 접수했습니다.\n\n"
        f"현재 {tone_desc} 톤의 {intent_label} 전문 에이전트를 준비 중입니다. "
        f"곧 더 정확한 답변을 드릴 수 있도록 업데이트될 예정입니다.\n\n"
        f"기종: {profile.name}\n"
        f"분류: {'보급형' if profile.tier == 'entry' else '전문가용'}\n"
        f"의도: {intent_label}"
    )

    if state.get("needs_disclaimer"):
        answer += f"\n\n{MEDICAL_DISCLAIMER}"

    return {"answer": answer}
