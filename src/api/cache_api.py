"""캐시 관리 API 엔드포인트 — T120"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.cache.semantic_cache import get_semantic_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cache", tags=["cache"])


class InvalidateResponse(BaseModel):
    deleted: int
    model_id: str
    intent: str | None = None


class CacheStatsResponse(BaseModel):
    total_entries: int
    total_hits: int
    by_model: dict


@router.delete("/{model_id}", response_model=InvalidateResponse)
async def invalidate_model_cache(model_id: str):
    """특정 기종의 캐시를 전체 무효화한다."""
    valid_models = {"270S", "580", "770S", "970S"}
    if model_id not in valid_models:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 기종: {model_id}")

    cache = get_semantic_cache()
    deleted = cache.invalidate(model_id=model_id)
    logger.info("캐시 무효화: model=%s, 삭제=%d건", model_id, deleted)

    return InvalidateResponse(deleted=deleted, model_id=model_id)


@router.delete("/{model_id}/{intent}", response_model=InvalidateResponse)
async def invalidate_model_intent_cache(model_id: str, intent: str):
    """특정 기종+의도 조합의 캐시를 무효화한다."""
    valid_models = {"270S", "580", "770S", "970S"}
    valid_intents = {"install", "connect", "troubleshoot", "clinical", "general"}

    if model_id not in valid_models:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 기종: {model_id}")
    if intent not in valid_intents:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 의도: {intent}")

    cache = get_semantic_cache()
    deleted = cache.invalidate(model_id=model_id, intent=intent)
    logger.info("캐시 무효화: model=%s, intent=%s, 삭제=%d건", model_id, intent, deleted)

    return InvalidateResponse(deleted=deleted, model_id=model_id, intent=intent)


@router.get("/stats", response_model=CacheStatsResponse)
async def cache_stats():
    """캐시 통계를 조회한다."""
    cache = get_semantic_cache()
    stats = cache.get_stats()

    return CacheStatsResponse(
        total_entries=stats["total_entries"],
        total_hits=stats["total_hits"],
        by_model=stats["by_model"],
    )
