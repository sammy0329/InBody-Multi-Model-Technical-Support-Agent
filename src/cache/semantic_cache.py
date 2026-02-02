"""시멘틱 캐시 모듈 — T111~T115

사용자 질문의 의미적 유사도를 기반으로 이전 응답을 캐싱한다.
Chroma 벡터 DB의 semantic_cache 컬렉션을 사용하며,
기종별 격리 + 의도별 TTL + guardrail_passed 검증을 적용한다.
"""

import json
import logging
import re
import time
import uuid

import chromadb
from chromadb.api.models.Collection import Collection

from src.config import settings
from src.rag.vectorstore import get_chroma_client, get_embeddings

logger = logging.getLogger(__name__)

CACHE_COLLECTION_NAME = "semantic_cache"

_ERROR_CODE_RE = re.compile(r"[Ee]\d{3}")


def extract_error_code(text: str) -> str | None:
    """텍스트에서 에러 코드(E001 등)를 추출한다."""
    match = _ERROR_CODE_RE.search(text)
    return match.group(0).upper() if match else None

# 의도별 TTL 매핑 (초)
_TTL_MAP: dict[str, int] = {
    "troubleshoot": settings.cache_ttl_troubleshoot,
    "install": settings.cache_ttl_install,
    "connect": settings.cache_ttl_connect,
    "clinical": settings.cache_ttl_clinical,
    "general": settings.cache_ttl_general,
}


class CacheEntry:
    """캐시 조회 결과를 담는 데이터 클래스."""

    def __init__(
        self,
        response: str,
        identified_model: str,
        intent: str,
        support_level: str | None,
        disclaimer_included: bool,
        image_urls: list[str],
        cache_id: str,
        similarity: float,
    ):
        self.response = response
        self.identified_model = identified_model
        self.intent = intent
        self.support_level = support_level
        self.disclaimer_included = disclaimer_included
        self.image_urls = image_urls
        self.cache_id = cache_id
        self.similarity = similarity


class SemanticCache:
    """Chroma 기반 시멘틱 캐시.

    기종별 격리, 의도별 TTL, guardrail_passed 검증을 적용한다.
    """

    def __init__(self) -> None:
        self._client: chromadb.ClientAPI = get_chroma_client()
        self._embeddings = get_embeddings()
        self._collection: Collection = self._client.get_or_create_collection(
            name=CACHE_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def _get_ttl(self, intent: str) -> int:
        return _TTL_MAP.get(intent, settings.cache_ttl_general)

    def _embed_query(self, text: str) -> list[float]:
        return self._embeddings.embed_query(text)

    def lookup(
        self,
        query: str,
        model_id: str,
        threshold: float | None = None,
    ) -> CacheEntry | None:
        """캐시에서 유사 질문을 조회한다 (T112).

        Args:
            query: 사용자 질문
            model_id: 기종 ID (격리 필터)
            threshold: 유사도 임계값 (None이면 config 기본값)

        Returns:
            CacheEntry 또는 None (미스)
        """
        if not settings.enable_semantic_cache:
            return None

        if threshold is None:
            threshold = settings.cache_similarity_threshold

        query_embedding = self._embed_query(query)

        # 에러 코드가 포함된 쿼리는 동일 에러 코드 캐시만 조회
        error_code = extract_error_code(query)
        if error_code:
            where = {
                "$and": [
                    {"identified_model": model_id},
                    {"error_code": error_code},
                ]
            }
        else:
            where = {"identified_model": model_id}

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=1,
            where=where,
            include=["metadatas", "distances", "documents"],
        )

        if not results["ids"] or not results["ids"][0]:
            return None

        # Chroma cosine distance = 1 - similarity
        distance = results["distances"][0][0]
        similarity = 1.0 - distance

        if similarity < threshold:
            logger.debug(
                "캐시 미스 (유사도 %.3f < %.3f): model=%s, query=%.30s...",
                similarity, threshold, model_id, query,
            )
            return None

        metadata = results["metadatas"][0][0]
        cache_id = results["ids"][0][0]

        # TTL 만료 확인
        created_at = metadata.get("created_at", 0)
        intent = metadata.get("intent", "general")
        ttl = self._get_ttl(intent)

        if time.time() - created_at > ttl:
            logger.info(
                "캐시 TTL 만료: id=%s, intent=%s, age=%ds",
                cache_id, intent, int(time.time() - created_at),
            )
            self._collection.delete(ids=[cache_id])
            return None

        # 히트 카운터 증가
        hit_count = metadata.get("hit_count", 0) + 1
        self._collection.update(
            ids=[cache_id],
            metadatas=[{**metadata, "hit_count": hit_count}],
        )

        image_urls_raw = metadata.get("image_urls", "[]")
        try:
            image_urls = json.loads(image_urls_raw)
        except (json.JSONDecodeError, TypeError):
            image_urls = []

        logger.info(
            "캐시 히트 (유사도 %.3f): model=%s, intent=%s, id=%s",
            similarity, model_id, intent, cache_id,
        )

        return CacheEntry(
            response=metadata["response"],
            identified_model=model_id,
            intent=intent,
            support_level=metadata.get("support_level"),
            disclaimer_included=metadata.get("disclaimer_included", False),
            image_urls=image_urls,
            cache_id=cache_id,
            similarity=similarity,
        )

    def store(
        self,
        query: str,
        model_id: str,
        intent: str,
        response: str,
        support_level: str | None = None,
        disclaimer_included: bool = False,
        image_urls: list[str] | None = None,
        guardrail_passed: bool = True,
    ) -> str | None:
        """응답을 캐시에 저장한다 (T113).

        guardrail_passed=True인 응답만 저장한다.

        Returns:
            캐시 ID 또는 None (저장 거부)
        """
        if not settings.enable_semantic_cache:
            return None

        if not guardrail_passed:
            logger.debug("가드레일 미통과 응답은 캐시하지 않음")
            return None

        cache_id = str(uuid.uuid4())
        query_embedding = self._embed_query(query)

        metadata = {
            "identified_model": model_id,
            "intent": intent,
            "response": response,
            "support_level": support_level or "",
            "disclaimer_included": disclaimer_included,
            "image_urls": json.dumps(image_urls or [], ensure_ascii=False),
            "guardrail_passed": True,
            "created_at": int(time.time()),
            "hit_count": 0,
            "error_code": extract_error_code(query) or "",
        }

        self._collection.add(
            ids=[cache_id],
            embeddings=[query_embedding],
            documents=[query],
            metadatas=[metadata],
        )

        logger.info(
            "캐시 저장: model=%s, intent=%s, id=%s",
            model_id, intent, cache_id,
        )
        return cache_id

    def invalidate(
        self,
        model_id: str,
        intent: str | None = None,
    ) -> int:
        """캐시를 무효화한다 (T114).

        Args:
            model_id: 기종 ID
            intent: 의도 (None이면 해당 기종 전체 삭제)

        Returns:
            삭제된 항목 수
        """
        where: dict = {"identified_model": model_id}
        if intent:
            where = {
                "$and": [
                    {"identified_model": model_id},
                    {"intent": intent},
                ]
            }

        # 삭제 대상 조회
        results = self._collection.get(where=where, include=[])
        ids = results["ids"]

        if not ids:
            return 0

        self._collection.delete(ids=ids)
        logger.info(
            "캐시 무효화: model=%s, intent=%s, 삭제=%d건",
            model_id, intent or "(전체)", len(ids),
        )
        return len(ids)

    def get_stats(self) -> dict:
        """캐시 통계를 반환한다 (T115).

        Returns:
            기종별 캐시 항목 수, 총 항목 수, 총 히트 수
        """
        total = self._collection.count()

        if total == 0:
            return {"total_entries": 0, "by_model": {}, "total_hits": 0}

        all_data = self._collection.get(include=["metadatas"])
        by_model: dict[str, dict] = {}
        total_hits = 0

        for metadata in all_data["metadatas"]:
            model_id = metadata.get("identified_model", "unknown")
            intent = metadata.get("intent", "unknown")
            hits = metadata.get("hit_count", 0)
            total_hits += hits

            if model_id not in by_model:
                by_model[model_id] = {"entries": 0, "hits": 0, "by_intent": {}}

            by_model[model_id]["entries"] += 1
            by_model[model_id]["hits"] += hits

            if intent not in by_model[model_id]["by_intent"]:
                by_model[model_id]["by_intent"][intent] = {"entries": 0, "hits": 0}

            by_model[model_id]["by_intent"][intent]["entries"] += 1
            by_model[model_id]["by_intent"][intent]["hits"] += hits

        return {
            "total_entries": total,
            "total_hits": total_hits,
            "by_model": by_model,
        }


# 싱글톤 인스턴스
_cache_instance: SemanticCache | None = None


def get_semantic_cache() -> SemanticCache:
    """SemanticCache 싱글톤을 반환한다."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SemanticCache()
    return _cache_instance
