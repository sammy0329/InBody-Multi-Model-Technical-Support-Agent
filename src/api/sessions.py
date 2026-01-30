"""세션 관리 API 엔드포인트 — T061"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.graph.workflow import get_checkpointer

router = APIRouter(prefix="/api/v1", tags=["sessions"])


class SessionState(BaseModel):
    thread_id: str
    identified_model: str | None = None
    intent: str | None = None
    message_count: int = 0


@router.get("/sessions/{thread_id}", response_model=SessionState)
async def get_session(thread_id: str):
    """세션 상태를 조회한다."""
    checkpointer = get_checkpointer()
    config = {"configurable": {"thread_id": thread_id}}

    checkpoint = checkpointer.get(config)
    if not checkpoint:
        raise HTTPException(status_code=404, detail=f"세션 '{thread_id}'을(를) 찾을 수 없습니다")

    state = checkpoint.get("channel_values", {})
    messages = state.get("messages", [])

    return SessionState(
        thread_id=thread_id,
        identified_model=state.get("identified_model"),
        intent=state.get("intent"),
        message_count=len(messages),
    )


@router.delete("/sessions/{thread_id}", status_code=204)
async def delete_session(thread_id: str):
    """세션을 삭제한다."""
    checkpointer = get_checkpointer()
    config = {"configurable": {"thread_id": thread_id}}

    checkpoint = checkpointer.get(config)
    if not checkpoint:
        raise HTTPException(status_code=404, detail=f"세션 '{thread_id}'을(를) 찾을 수 없습니다")

    checkpointer.delete_thread(thread_id)

    return None
