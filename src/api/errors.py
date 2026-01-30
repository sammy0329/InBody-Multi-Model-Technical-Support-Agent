"""에러 코드 조회 API 엔드포인트 — T044"""

import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from src.db.database import async_session_factory
from src.db.schemas import ErrorCodeTable
from src.models.inbody_models import SUPPORTED_MODELS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["errors"])


@router.get("/models/{model_id}/errors")
async def list_errors(model_id: str):
    """특정 기종의 전체 에러 코드 목록을 반환한다."""
    if model_id not in SUPPORTED_MODELS:
        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 기종입니다",
        )

    async with async_session_factory() as session:
        result = await session.execute(
            select(ErrorCodeTable).where(ErrorCodeTable.model_id == model_id)
        )
        rows = result.scalars().all()

    return {
        "model_id": model_id,
        "errors": [
            {
                "code": row.code,
                "title": row.title,
                "support_level": row.support_level,
            }
            for row in rows
        ],
        "total": len(rows),
    }


@router.get("/models/{model_id}/errors/{error_code}")
async def get_error(model_id: str, error_code: str):
    """특정 기종의 에러 코드 정보를 조회한다."""
    if model_id not in SUPPORTED_MODELS:
        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 기종입니다",
        )

    async with async_session_factory() as session:
        result = await session.execute(
            select(ErrorCodeTable).where(
                ErrorCodeTable.model_id == model_id,
                ErrorCodeTable.code == error_code,
            )
        )
        row = result.scalar_one_or_none()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="해당 기종에서 에러 코드를 찾을 수 없습니다",
        )

    return {
        "code": row.code,
        "model_id": row.model_id,
        "title": row.title,
        "description": row.description,
        "cause": row.cause,
        "support_level": row.support_level,
        "resolution_steps": row.resolution_steps,
        "escalation_note": row.escalation_note,
    }
