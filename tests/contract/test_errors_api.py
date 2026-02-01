"""에러 코드 API 계약 테스트

GET /api/v1/models/{model_id}/errors 엔드포인트의
응답 구조 및 데이터 정확성을 검증한다.

주의: 이 테스트는 실제 DB에 시드 데이터가 있어야 정상 작동한다.
seeded_db fixture를 사용하여 인메모리 DB에 시드 데이터를 주입한다.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.db.schemas import Base, ErrorCodeTable

SEED_PATH = Path(__file__).parent.parent.parent / "data" / "seed" / "error_codes.json"


@pytest.fixture
async def seeded_engine():
    """에러 코드 시드 데이터가 포함된 인메모리 DB 엔진"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 시드 데이터 삽입
    seed_data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        for item in seed_data:
            session.add(ErrorCodeTable(**item))
        await session.commit()

    yield engine
    await engine.dispose()


@pytest.fixture
async def seeded_client(seeded_engine):
    """시드된 DB를 사용하는 FastAPI 테스트 클라이언트"""
    session_factory = sessionmaker(seeded_engine, class_=AsyncSession, expire_on_commit=False)

    with patch("src.api.errors.async_session_factory", session_factory):
        from httpx import ASGITransport, AsyncClient
        from src.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.mark.contract
async def test_list_errors_270s(seeded_client):
    """GET /models/270S/errors가 에러 목록을 반환한다."""
    resp = await seeded_client.get("/api/v1/models/270S/errors")
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_id"] == "270S"
    assert isinstance(data["errors"], list)
    assert data["total"] >= 1


@pytest.mark.contract
async def test_list_errors_response_shape(seeded_client):
    """에러 목록 항목이 필수 필드를 가진다."""
    resp = await seeded_client.get("/api/v1/models/270S/errors")
    for error in resp.json()["errors"]:
        assert "code" in error
        assert "title" in error
        assert "support_level" in error


@pytest.mark.contract
async def test_get_error_detail(seeded_client):
    """GET /models/270S/errors/E001이 상세 정보를 반환한다."""
    resp = await seeded_client.get("/api/v1/models/270S/errors/E001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == "E001"
    assert data["model_id"] == "270S"
    assert "title" in data
    assert "description" in data
    assert "cause" in data
    assert "support_level" in data
    assert "resolution_steps" in data


@pytest.mark.contract
async def test_get_error_404_unknown_code(seeded_client):
    """존재하지 않는 에러 코드는 404를 반환한다."""
    resp = await seeded_client.get("/api/v1/models/270S/errors/E999")
    assert resp.status_code == 404


@pytest.mark.contract
async def test_list_errors_400_unsupported_model(seeded_client):
    """지원하지 않는 기종은 400을 반환한다."""
    resp = await seeded_client.get("/api/v1/models/999X/errors")
    assert resp.status_code == 400
