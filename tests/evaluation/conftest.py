"""Evaluation 테스트 전용 픽스처 — DB 시딩 및 세션 팩토리 오버라이드"""

import json
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.db.schemas import Base, ErrorCodeTable, PeripheralCompatibilityTable

SEED_DIR = Path(__file__).parent.parent.parent / "data" / "seed"


@pytest.fixture
async def seeded_session_factory():
    """에러 코드 + 주변기기 호환 시드 데이터가 포함된 인메모리 DB 세션 팩토리"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 에러 코드 시드 데이터 삽입
    seed_path = SEED_DIR / "error_codes.json"
    seed_data = json.loads(seed_path.read_text(encoding="utf-8"))

    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        for item in seed_data:
            session.add(ErrorCodeTable(**item))
        await session.commit()

    # 주변기기 호환 시드 데이터 삽입
    peripheral_path = SEED_DIR / "peripheral_compatibility.json"
    peripheral_data = json.loads(peripheral_path.read_text(encoding="utf-8"))

    async with factory() as session:
        for item in peripheral_data:
            session.add(PeripheralCompatibilityTable(**item))
        await session.commit()

    yield factory
    await engine.dispose()
