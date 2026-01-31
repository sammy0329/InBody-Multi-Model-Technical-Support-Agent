"""Streamlit 메인 채팅 앱 -- T070, T071"""

import streamlit as st

from api_client import get_client
from components import generate_thread_id, render_sidebar

# ── 페이지 설정 ──
st.set_page_config(
    page_title="InBody Tech-Master",
    page_icon="\U0001f4aa",
    layout="wide",
)

# ── session_state 초기화 ──
if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "last_sent_model" not in st.session_state:
    st.session_state["last_sent_model"] = None

# ── 사이드바 렌더링 ──
selected_model = render_sidebar()

# ── 채팅 이력 표시 ──
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("metadata"):
            _meta = msg["metadata"]
            with st.expander("응답 정보", expanded=False):
                if _meta.get("identified_model"):
                    st.caption(f"기종: {_meta['identified_model']}")
                if _meta.get("intent"):
                    st.caption(f"의도: {_meta['intent']}")
                if _meta.get("support_level"):
                    st.caption(f"지원 수준: {_meta['support_level']}")

# ── 노드 레이블 매핑 ──
NODE_LABELS = {
    "model_router": "기종 식별 중...",
    "intent_router": "의도 분류 중...",
    "troubleshoot_agent": "트러블슈팅 분석 중...",
    "install_agent": "설치 안내 생성 중...",
    "connect_agent": "연동 정보 확인 중...",
    "clinical_agent": "임상 정보 분석 중...",
    "placeholder_agent": "응답 생성 중...",
    "guardrail": "안전 검증 중...",
    "fix_response": "응답 수정 중...",
}

# ── 사용자 입력 ──
if user_input := st.chat_input("질문을 입력하세요"):
    # 기종 선택이 바뀌었으면 prefix 재전송
    if selected_model and selected_model != st.session_state["last_sent_model"]:
        api_message = f"InBody {selected_model} 사용자입니다. {user_input}"
        st.session_state["last_sent_model"] = selected_model
    else:
        api_message = user_input

    # 사용자 메시지 표시 (원본)
    st.session_state["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # ── 어시스턴트 응답 ──
    with st.chat_message("assistant"):
        client = get_client()
        thread_id = st.session_state["thread_id"]

        try:
            status_container = st.status("응답 생성 중...", expanded=False)
            response_placeholder = st.empty()

            full_response = ""
            metadata = {}

            for event in client.chat_stream(api_message, thread_id):
                event_type = event.get("type")

                if event_type == "node_start":
                    node = event.get("node", "")
                    label = NODE_LABELS.get(node, f"{node} 처리 중...")
                    status_container.update(label=label, state="running")

                elif event_type == "token":
                    full_response += event.get("content", "")
                    response_placeholder.markdown(full_response + "\u258c")

                elif event_type == "done":
                    full_response = event.get("response", full_response)
                    response_placeholder.markdown(full_response)
                    metadata = {
                        "identified_model": event.get("identified_model"),
                        "intent": event.get("intent"),
                        "support_level": event.get("support_level"),
                    }
                    status_container.update(label="응답 완료", state="complete")

                elif event_type == "error":
                    error_msg = event.get("content", "오류가 발생했습니다.")
                    response_placeholder.error(error_msg)
                    status_container.update(label="오류 발생", state="error")
                    full_response = error_msg

            st.session_state["messages"].append({
                "role": "assistant",
                "content": full_response,
                "metadata": metadata if metadata else None,
            })

        except Exception as e:
            st.warning(f"스트리밍 연결 실패: {e}")
            st.info("동기 API로 재시도합니다...")
            try:
                result = client.chat(api_message, thread_id)
                response = result.get("response", "응답을 받을 수 없습니다.")
                st.markdown(response)
                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": response,
                })
            except Exception:
                st.error("서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.")
