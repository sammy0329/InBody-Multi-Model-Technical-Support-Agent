"""기종 정보 API 엔드포인트 — T060"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.models.inbody_models import INBODY_MODELS

router = APIRouter(prefix="/api/v1", tags=["models"])


class ModelSummary(BaseModel):
    model_id: str
    name: str
    tier: str
    description: str


class ModelDetail(BaseModel):
    model_id: str
    name: str
    tier: str
    install_type: str
    tone_profile: str
    measurement_items: list[str]
    description: str


@router.get("/models", response_model=list[ModelSummary])
async def list_models():
    """지원 기종 목록을 반환한다."""
    return [
        ModelSummary(
            model_id=p.model_id,
            name=p.name,
            tier=p.tier,
            description=p.description,
        )
        for p in INBODY_MODELS.values()
    ]


@router.get("/models/{model_id}", response_model=ModelDetail)
async def get_model(model_id: str):
    """특정 기종의 상세 정보를 반환한다."""
    profile = INBODY_MODELS.get(model_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"기종 '{model_id}'을(를) 찾을 수 없습니다")

    return ModelDetail(
        model_id=profile.model_id,
        name=profile.name,
        tier=profile.tier,
        install_type=profile.install_type,
        tone_profile=profile.tone_profile,
        measurement_items=list(profile.measurement_items),
        description=profile.description,
    )
