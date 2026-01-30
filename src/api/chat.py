"""채팅 API 엔드포인트 — T038"""

import logging

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from src.graph.workflow import get_compiled_workflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    thread_id: str


class SourceInfo(BaseModel):
    title: str
    section: str
    page: int | None = None


class ChatResponse(BaseModel):
    response: str
    identified_model: str | None = None
    intent: str | None = None
    support_level: str | None = None
    disclaimer_included: bool = False
    sources: list[SourceInfo] = []
    image_urls: list[str] = []


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """사용자 메시지를 받아 AI 에이전트 응답을 반환한다."""
    if not request.message.strip():
        raise HTTPException(
            status_code=400,
            detail="message와 thread_id는 필수입니다",
        )

    if not request.thread_id.strip():
        raise HTTPException(
            status_code=400,
            detail="message와 thread_id는 필수입니다",
        )

    try:
        workflow = get_compiled_workflow()

        initial_state = {
            "messages": [HumanMessage(content=request.message)],
            "identified_model": None,
            "model_tier": None,
            "intent": None,
            "retrieved_docs": [],
            "image_urls": [],
            "error_code": None,
            "support_level": None,
            "tone_profile": None,
            "needs_disclaimer": False,
            "answer": None,
            "guardrail_passed": None,
        }

        result = await workflow.ainvoke(initial_state)

        return ChatResponse(
            response=result.get("answer", "응답을 생성할 수 없습니다."),
            identified_model=result.get("identified_model"),
            intent=result.get("intent"),
            support_level=result.get("support_level"),
            disclaimer_included=result.get("needs_disclaimer", False),
            sources=[],
            image_urls=result.get("image_urls", []),
        )
    except Exception:
        logger.exception("채팅 처리 중 오류 발생")
        raise HTTPException(status_code=500, detail="서버 오류가 발생했습니다")
