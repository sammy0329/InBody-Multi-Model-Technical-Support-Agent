"""채팅 API 엔드포인트 — T038, T059, T062"""

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
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
    guardrail_passed: bool | None = None
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
            "guardrail_retry_count": 0,
            "guardrail_violations": [],
            "guardrail_suggestion": None,
        }

        config = {"configurable": {"thread_id": request.thread_id}}
        result = await workflow.ainvoke(initial_state, config=config)

        return ChatResponse(
            response=result.get("answer", "응답을 생성할 수 없습니다."),
            identified_model=result.get("identified_model"),
            intent=result.get("intent"),
            support_level=result.get("support_level"),
            disclaimer_included=result.get("needs_disclaimer", False),
            guardrail_passed=result.get("guardrail_passed"),
            sources=[],
            image_urls=result.get("image_urls", []),
        )
    except Exception:
        logger.exception("채팅 처리 중 오류 발생")
        raise HTTPException(status_code=500, detail="서버 오류가 발생했습니다")


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """SSE 스트리밍으로 AI 에이전트 응답을 반환한다 (T059)."""
    if not request.message.strip() or not request.thread_id.strip():
        raise HTTPException(
            status_code=400,
            detail="message와 thread_id는 필수입니다",
        )

    async def event_generator():
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
                "guardrail_retry_count": 0,
                "guardrail_violations": [],
                "guardrail_suggestion": None,
            }

            config = {"configurable": {"thread_id": request.thread_id}}

            async for event in workflow.astream_events(
                initial_state, config=config, version="v2"
            ):
                kind = event.get("event")

                # LLM 토큰 스트리밍
                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        payload = json.dumps(
                            {"type": "token", "content": chunk.content},
                            ensure_ascii=False,
                        )
                        yield f"data: {payload}\n\n"

                # 노드 시작
                elif kind == "on_chain_start" and event.get("name") in {
                    "model_router", "intent_router",
                    "troubleshoot_agent", "install_agent",
                    "connect_agent", "clinical_agent",
                    "placeholder_agent", "guardrail", "fix_response",
                }:
                    payload = json.dumps(
                        {"type": "node_start", "node": event["name"]},
                        ensure_ascii=False,
                    )
                    yield f"data: {payload}\n\n"

            # 스트리밍 완료 후 체크포인터에서 최종 상태 조회
            snapshot = await workflow.aget_state(config)
            final = snapshot.values
            done_payload = json.dumps(
                {
                    "type": "done",
                    "response": final.get("answer", ""),
                    "identified_model": final.get("identified_model"),
                    "intent": final.get("intent"),
                    "support_level": final.get("support_level"),
                    "guardrail_passed": final.get("guardrail_passed"),
                    "disclaimer_included": final.get("needs_disclaimer", False),
                },
                ensure_ascii=False,
            )
            yield f"data: {done_payload}\n\n"

        except Exception:
            logger.exception("SSE 스트리밍 중 오류 발생")
            error_payload = json.dumps(
                {"type": "error", "content": "서버 오류가 발생했습니다"},
                ensure_ascii=False,
            )
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
