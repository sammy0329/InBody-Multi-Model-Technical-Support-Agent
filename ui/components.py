"""사이드바 및 재사용 UI 컴포넌트 -- T069"""

import uuid

import streamlit as st

from api_client import get_client


def generate_thread_id() -> str:
    """UUID 기반 thread_id를 생성한다."""
    return str(uuid.uuid4())


def render_sidebar() -> str | None:
    """사이드바를 렌더링하고, 선택된 기종 model_id를 반환한다.

    Returns:
        str: 선택된 기종의 model_id (예: "770S")
        None: "선택 안 함" 상태
    """
    with st.sidebar:
        st.title("InBody Tech-Master")
        st.caption("InBody 기종별 기술 지원 챗봇")

        st.divider()

        selected_model = _render_model_selector()

        st.divider()

        _render_session_controls()

        st.divider()

        _render_system_status()

    return selected_model


@st.cache_data(ttl=300)
def _fetch_models() -> list[dict]:
    """기종 목록을 캐시하여 반환한다."""
    return get_client().list_models()


def _render_model_selector() -> str | None:
    """기종 선택 selectbox를 렌더링한다."""
    st.subheader("기종 선택")

    models = _fetch_models()

    if not models:
        st.warning("기종 정보를 불러올 수 없습니다.")
        return None

    model_options = {m["name"]: m["model_id"] for m in models}
    options = ["선택 안 함"] + list(model_options.keys())

    selected = st.selectbox(
        "사용 중인 기종을 선택하세요",
        options,
        key="model_selector",
        help="기종을 선택하면 해당 기종에 맞는 지원을 받을 수 있습니다.",
    )

    if selected == "선택 안 함":
        st.info("기종을 선택하지 않아도 채팅할 수 있습니다.")
        return None

    model_id = model_options[selected]
    model_info = next((m for m in models if m["model_id"] == model_id), None)
    if model_info:
        tier_label = "보급형" if model_info["tier"] == "entry" else "전문가용"
        st.success(f"{selected} ({tier_label})")

    return model_id


def _render_session_controls():
    """세션 초기화 버튼을 렌더링한다."""
    st.subheader("세션 관리")

    if st.button("대화 초기화", use_container_width=True, type="secondary"):
        client = get_client()
        thread_id = st.session_state.get("thread_id")
        if thread_id:
            client.delete_session(thread_id)
        st.session_state["messages"] = []
        st.session_state["thread_id"] = generate_thread_id()
        st.session_state["last_sent_model"] = None
        st.rerun()


@st.cache_data(ttl=60)
def _fetch_health() -> dict:
    """헬스 체크 결과를 캐시하여 반환한다."""
    return get_client().health_check()


def _render_system_status():
    """시스템 상태를 표시한다."""
    st.subheader("시스템 상태")

    health = _fetch_health()
    status = health.get("status", "unknown")

    if status == "healthy":
        st.success("시스템 정상")
    elif status == "degraded":
        st.warning("시스템 일부 장애")
    else:
        st.error("백엔드 연결 불가")

    components = health.get("components", {})
    if components:
        label_map = {"llm": "LLM", "vector_db": "벡터DB", "structured_db": "구조DB"}
        cols = st.columns(len(components))
        for i, (name, comp_status) in enumerate(components.items()):
            with cols[i]:
                icon = ":white_check_mark:" if comp_status == "ok" else ":x:"
                st.caption(f"{icon} {label_map.get(name, name)}")
