"""JSON 시드 데이터를 DB에 로드하는 모듈"""

import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.schemas import ErrorCodeTable, PeripheralCompatibilityTable

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "seed"


async def seed_error_codes(session: AsyncSession) -> int:
    """에러 코드 시드 데이터 로드 — 이미 존재하면 건너뜀"""
    existing = await session.execute(select(ErrorCodeTable.id).limit(1))
    if existing.scalar_one_or_none() is not None:
        logger.info("에러 코드 데이터가 이미 존재합니다. 건너뜁니다.")
        return 0

    data_path = DATA_DIR / "error_codes.json"
    with open(data_path, encoding="utf-8") as f:
        error_codes = json.load(f)

    count = 0
    for ec in error_codes:
        row = ErrorCodeTable(**ec)
        session.add(row)
        count += 1

    await session.commit()
    logger.info("에러 코드 %d건 시딩 완료", count)
    return count


async def seed_peripherals(session: AsyncSession) -> int:
    """주변기기 호환표 시드 데이터 로드 — 이미 존재하면 건너뜀"""
    existing = await session.execute(select(PeripheralCompatibilityTable.id).limit(1))
    if existing.scalar_one_or_none() is not None:
        logger.info("호환표 데이터가 이미 존재합니다. 건너뜁니다.")
        return 0

    data_path = DATA_DIR / "peripheral_compatibility.json"
    with open(data_path, encoding="utf-8") as f:
        peripherals = json.load(f)

    count = 0
    for p in peripherals:
        row = PeripheralCompatibilityTable(**p)
        session.add(row)
        count += 1

    await session.commit()
    logger.info("호환표 %d건 시딩 완료", count)
    return count


async def seed_all(session: AsyncSession) -> dict[str, int]:
    """전체 시드 데이터 로드"""
    ec_count = await seed_error_codes(session)
    pc_count = await seed_peripherals(session)
    return {"error_codes": ec_count, "peripherals": pc_count}
