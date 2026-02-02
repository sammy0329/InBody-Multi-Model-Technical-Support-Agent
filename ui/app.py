"""Streamlit 메인 채팅 앱 -- T070, T071, T087"""

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

# ── '선택 안 함' 전환 시 세션 리셋 ──
if selected_model is None and st.session_state["last_sent_model"] is not None:
    st.session_state["thread_id"] = generate_thread_id()
    st.session_state["messages"] = []
    st.session_state["last_sent_model"] = None

# ── 기종 선택 버튼 (T087) ──
MODEL_CHOICES = [
    ("InBody 270S", "270S"),
    ("InBody 580", "580"),
    ("InBody 770S", "770S"),
    ("InBody 970S", "970S"),
]


def _handle_model_selection(model_id: str) -> None:
    """기종 선택 버튼 클릭 시 상태 업데이트 후 rerun."""
    original_q = st.session_state["messages"][-2]["content"]
    st.session_state["messages"] = []
    st.session_state["thread_id"] = generate_thread_id()
    st.session_state["_model_from_chat"] = model_id
    st.session_state["pending_question"] = original_q
    st.rerun()


def _render_model_buttons() -> None:
    """기종 선택 버튼 4개를 한 줄에 렌더링한다."""
    st.markdown("---")
    cols = st.columns(len(MODEL_CHOICES))
    for j, (name, model_id) in enumerate(MODEL_CHOICES):
        with cols[j]:
            if st.button(
                name, key=f"select_{model_id}",
                use_container_width=True, type="primary",
            ):
                _handle_model_selection(model_id)


# ── 예시 질문 ──
EXAMPLE_QUESTIONS = {
    "🔧 설치": [
        "제품 초기 세팅은 어떻게 하나요?",
        "본체 조립 방법을 알려주세요.",
    ],
    "🔌 연동": [
        "호환되는 프린터 목록을 알려주세요.",
        "PC 연결 방법이 궁금합니다.",
    ],
    "🛠️ 트러블슈팅": [
        "에러 코드 E013이 떠요.",
        "체중 측정이 안 됩니다.",
    ],
    "📊 측정 결과": [
        "체수분 수치가 높게 나왔는데 왜 그런가요?",
        "골격근량 결과를 어떻게 해석하나요?",
    ],
}

# ── pending question 체크 (st.rerun 없이 직접 처리) ──
_pending = st.session_state.pop("pending_question", None)

# ── 웰컴 메시지 (첫 방문 시에만) ──
if not st.session_state["messages"] and not _pending:
    st.markdown("### InBody 기술 지원 챗봇에 오신 것을 환영합니다")
    st.caption("사이드바에서 기종을 선택한 뒤, 아래 예시를 참고하여 질문해 주세요.")

# ── 예시 질문 버튼 (항상 표시, 접기/펼치기 가능) ──
_has_messages = bool(st.session_state["messages"])
with st.expander("💡 빠른 질문 예시", expanded=not _has_messages and not _pending):
    cols = st.columns(len(EXAMPLE_QUESTIONS))
    for col, (category, questions) in zip(cols, EXAMPLE_QUESTIONS.items()):
        with col:
            st.markdown(f"**{category}**")
            for q in questions:
                if st.button(q, key=q, use_container_width=True):
                    _pending = q

# ── 채팅 이력 표시 ──
_msg_count = len(st.session_state["messages"])
for _i, msg in enumerate(st.session_state["messages"]):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        _meta = msg.get("metadata") or {}
        # T087: 마지막 assistant 메시지가 기종 선택 필요 시 버튼 표시
        if (msg["role"] == "assistant"
                and _i == _msg_count - 1
                and _meta.get("needs_model_selection")):
            _render_model_buttons()
        elif _meta.get("identified_model") or _meta.get("intent"):
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
chat_input = st.chat_input("질문을 입력하세요")
user_input = _pending or chat_input
if user_input:
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

                elif event_type == "clear":
                    # 가드레일 위반 → fix_response 재생성 시 이전 스트리밍 초기화
                    full_response = ""
                    response_placeholder.empty()

                elif event_type == "token":
                    full_response += event.get("content", "")
                    response_placeholder.markdown(full_response + "\u258c")

                elif event_type == "done":
                    full_response = event.get("response", full_response)
                    response_placeholder.markdown(full_response)
                    _needs_model = (
                        not event.get("identified_model")
                        and not event.get("intent")
                        and "기종" in full_response
                        and not full_response.startswith("요청하신")
                        and not full_response.startswith("죄송합니다")
                    )
                    metadata = {
                        "identified_model": event.get("identified_model"),
                        "intent": event.get("intent"),
                        "support_level": event.get("support_level"),
                        "needs_model_selection": _needs_model,
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

            # T087: 기종 선택 필요 시 버튼 즉시 표시
            if metadata.get("needs_model_selection"):
                _render_model_buttons()
            elif metadata.get("identified_model") or metadata.get("intent"):
                with st.expander("응답 정보", expanded=False):
                    if metadata.get("identified_model"):
                        st.caption(f"기종: {metadata['identified_model']}")
                    if metadata.get("intent"):
                        st.caption(f"의도: {metadata['intent']}")
                    if metadata.get("support_level"):
                        st.caption(f"지원 수준: {metadata['support_level']}")

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
