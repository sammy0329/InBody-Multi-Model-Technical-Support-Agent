"""모델 API 계약 테스트

GET /api/v1/models, GET /api/v1/models/{model_id} 엔드포인트의
응답 구조 및 데이터 정확성을 검증한다.
"""

import pytest

from src.models.inbody_models import SUPPORTED_MODELS


@pytest.mark.contract
async def test_list_models_returns_four(client):
    """GET /models는 4개 기종을 반환한다."""
    resp = await client.get("/api/v1/models")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 4


@pytest.mark.contract
async def test_list_models_response_shape(client):
    """각 모델 항목이 필수 필드(model_id, name, tier, description)를 가진다."""
    resp = await client.get("/api/v1/models")
    for item in resp.json():
        assert "model_id" in item
        assert "name" in item
        assert "tier" in item
        assert "description" in item


@pytest.mark.contract
async def test_list_models_contains_all_supported(client):
    """반환된 model_id 집합이 SUPPORTED_MODELS와 일치한다."""
    resp = await client.get("/api/v1/models")
    returned_ids = {item["model_id"] for item in resp.json()}
    assert returned_ids == SUPPORTED_MODELS


@pytest.mark.contract
async def test_get_model_detail_270s(client):
    """GET /models/270S가 보급형 접이식 정보를 반환한다."""
    resp = await client.get("/api/v1/models/270S")
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_id"] == "270S"
    assert data["tier"] == "entry"
    assert data["install_type"] == "foldable"
    assert data["tone_profile"] == "casual"
    assert isinstance(data["measurement_items"], list)
    assert len(data["measurement_items"]) > 0


@pytest.mark.contract
async def test_get_model_detail_970s(client):
    """GET /models/970S가 전문가용 분리형 정보를 반환한다."""
    resp = await client.get("/api/v1/models/970S")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tier"] == "professional"
    assert data["install_type"] == "separable"
    assert data["tone_profile"] == "professional"


@pytest.mark.contract
async def test_get_model_404_unsupported(client):
    """존재하지 않는 기종은 404를 반환한다."""
    resp = await client.get("/api/v1/models/999X")
    assert resp.status_code == 404
