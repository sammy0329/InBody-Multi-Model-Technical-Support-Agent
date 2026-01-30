"""헬스 체크 엔드포인트 — T039"""

import logging

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from src.config import settings
from src.db.database import engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["health"])


class ComponentStatus(BaseModel):
    llm: str = "ok"
    vector_db: str = "ok"
    structured_db: str = "ok"


class HealthResponse(BaseModel):
    status: str = "healthy"
    components: ComponentStatus = ComponentStatus()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """서비스 상태를 확인한다."""
    components = ComponentStatus()

    # LLM (OpenAI API) 상태 확인
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        await client.models.list()
    except Exception:
        logger.warning("LLM 상태 확인 실패")
        components.llm = "down"

    # Vector DB (Chroma) 상태 확인
    try:
        import chromadb

        chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        chroma_client.heartbeat()
    except Exception:
        logger.warning("Vector DB 상태 확인 실패")
        components.vector_db = "down"

    # Structured DB 상태 확인
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        logger.warning("Structured DB 상태 확인 실패")
        components.structured_db = "down"

    # 전체 상태 판단
    statuses = [components.llm, components.vector_db, components.structured_db]
    if all(s == "ok" for s in statuses):
        overall = "healthy"
    else:
        overall = "degraded"

    return HealthResponse(status=overall, components=components)
