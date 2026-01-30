"""주변기기 호환 조회 API 엔드포인트 — T051"""

import logging

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from src.db.database import async_session_factory
from src.db.schemas import PeripheralCompatibilityTable
from src.models.inbody_models import SUPPORTED_MODELS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["peripherals"])


@router.get("/models/{model_id}/peripherals")
async def list_peripherals(
    model_id: str,
    peripheral_type: str | None = Query(
        None, description="주변기기 유형 필터 (printer, pc, barcode_reader, usb)"
    ),
):
    """특정 기종의 주변기기 호환 목록을 반환한다."""
    if model_id not in SUPPORTED_MODELS:
        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 기종입니다",
        )

    async with async_session_factory() as session:
        query = select(PeripheralCompatibilityTable).where(
            PeripheralCompatibilityTable.model_id == model_id
        )
        if peripheral_type:
            query = query.where(
                PeripheralCompatibilityTable.peripheral_type == peripheral_type
            )
        result = await session.execute(query)
        rows = result.scalars().all()

    return {
        "model_id": model_id,
        "peripherals": [
            {
                "peripheral_type": row.peripheral_type,
                "peripheral_name": row.peripheral_name,
                "is_compatible": row.is_compatible,
                "connection_method": row.connection_method,
                "setup_steps": row.setup_steps,
            }
            for row in rows
        ],
        "total": len(rows),
    }


@router.get("/models/{model_id}/peripherals/{peripheral_name}/compatibility")
async def get_peripheral_compatibility(model_id: str, peripheral_name: str):
    """특정 기종의 특정 주변기기 호환 정보를 조회한다."""
    if model_id not in SUPPORTED_MODELS:
        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 기종입니다",
        )

    async with async_session_factory() as session:
        result = await session.execute(
            select(PeripheralCompatibilityTable).where(
                PeripheralCompatibilityTable.model_id == model_id,
                PeripheralCompatibilityTable.peripheral_name.ilike(
                    f"%{peripheral_name}%"
                ),
            )
        )
        row = result.scalar_one_or_none()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="해당 기종에서 주변기기 호환 정보를 찾을 수 없습니다",
        )

    return {
        "model_id": row.model_id,
        "peripheral_type": row.peripheral_type,
        "peripheral_name": row.peripheral_name,
        "is_compatible": row.is_compatible,
        "connection_method": row.connection_method,
        "setup_steps": row.setup_steps,
    }
