"""시멘틱 캐시 단위 테스트 — T123

lookup/store/invalidate/TTL 만료/기종 격리를 검증한다.
Chroma 인메모리 + mock embeddings 사용으로 LLM 키 불필요.
"""

import time
from unittest.mock import MagicMock, patch

import chromadb
import pytest

from src.cache.semantic_cache import CacheEntry, SemanticCache


# ──────────────────────────────────────────────
# 공통 픽스처
# ──────────────────────────────────────────────

class FakeEmbeddings:
    """동일 문자열 → 동일 벡터를 반환하는 가짜 임베딩."""

    def __init__(self):
        self._cache: dict[str, list[float]] = {}
        self._counter = 0

    def embed_query(self, text: str) -> list[float]:
        if text not in self._cache:
            # 문자열마다 고유한 벡터 할당 (차원=128)
            vec = [0.0] * 128
            vec[self._counter % 128] = 1.0
            self._cache[text] = vec
            self._counter += 1
        return self._cache[text]


@pytest.fixture
def cache():
    """인메모리 Chroma + 가짜 임베딩을 사용하는 SemanticCache."""
    fake_embeddings = FakeEmbeddings()
    client = chromadb.Client()

    with patch("src.cache.semantic_cache.get_chroma_client", return_value=client), \
         patch("src.cache.semantic_cache.get_embeddings", return_value=fake_embeddings), \
         patch("src.cache.semantic_cache.settings") as mock_settings:
        mock_settings.enable_semantic_cache = True
        mock_settings.cache_similarity_threshold = 0.92
        mock_settings.cache_ttl_troubleshoot = 604800
        mock_settings.cache_ttl_install = 2592000
        mock_settings.cache_ttl_connect = 1209600
        mock_settings.cache_ttl_clinical = 7776000
        mock_settings.cache_ttl_general = 2592000

        sc = SemanticCache()
        yield sc

        # cleanup
        try:
            client.delete_collection("semantic_cache")
        except Exception:
            pass


# ──────────────────────────────────────────────
# T123-1: store + lookup 기본 흐름
# ──────────────────────────────────────────────

class TestStoreAndLookup:
    """캐시 저장 후 조회 기본 동작 검증."""

    def test_store_returns_cache_id(self, cache):
        cache_id = cache.store(
            query="프린터 연결 방법",
            model_id="770S",
            intent="connect",
            response="프린터 연결 절차는...",
        )
        assert cache_id is not None
        assert isinstance(cache_id, str)

    def test_lookup_exact_match(self, cache):
        cache.store(
            query="프린터 연결 방법",
            model_id="770S",
            intent="connect",
            response="프린터 연결 절차는...",
        )
        # 동일 질문으로 조회 — 임계값 0으로 설정하여 정확 매칭 보장
        entry = cache.lookup(
            query="프린터 연결 방법",
            model_id="770S",
            threshold=0.0,
        )
        assert entry is not None
        assert entry.response == "프린터 연결 절차는..."
        assert entry.identified_model == "770S"
        assert entry.intent == "connect"

    def test_lookup_miss_different_query(self, cache):
        cache.store(
            query="프린터 연결 방법",
            model_id="770S",
            intent="connect",
            response="프린터 연결 절차는...",
        )
        # 전혀 다른 질문
        entry = cache.lookup(
            query="에러 코드 E013",
            model_id="770S",
            threshold=0.5,
        )
        assert entry is None

    def test_lookup_returns_none_when_empty(self, cache):
        entry = cache.lookup(query="아무 질문", model_id="270S")
        assert entry is None


# ──────────────────────────────────────────────
# T123-2: 기종 격리
# ──────────────────────────────────────────────

class TestModelIsolation:
    """캐시의 기종별 격리를 검증한다."""

    def test_different_model_not_returned(self, cache):
        """770S에 저장된 캐시가 580 조회 시 반환되지 않아야 한다."""
        cache.store(
            query="프린터 연결 방법",
            model_id="770S",
            intent="connect",
            response="770S 프린터 연결 절차는...",
        )
        entry = cache.lookup(
            query="프린터 연결 방법",
            model_id="580",
            threshold=0.0,
        )
        assert entry is None

    def test_same_model_returned(self, cache):
        """770S에 저장된 캐시가 770S 조회 시 반환되어야 한다."""
        cache.store(
            query="프린터 연결 방법",
            model_id="770S",
            intent="connect",
            response="770S 프린터 연결 절차는...",
        )
        entry = cache.lookup(
            query="프린터 연결 방법",
            model_id="770S",
            threshold=0.0,
        )
        assert entry is not None
        assert entry.response == "770S 프린터 연결 절차는..."

    @pytest.mark.parametrize("model_a,model_b", [
        ("270S", "580"),
        ("270S", "770S"),
        ("270S", "970S"),
        ("580", "770S"),
        ("580", "970S"),
        ("770S", "970S"),
    ])
    def test_cross_model_isolation(self, cache, model_a, model_b):
        """모든 기종 조합에서 교차 오염이 없어야 한다."""
        cache.store(
            query="설치 방법",
            model_id=model_a,
            intent="install",
            response=f"{model_a} 설치 절차는...",
        )
        entry = cache.lookup(query="설치 방법", model_id=model_b, threshold=0.0)
        assert entry is None


# ──────────────────────────────────────────────
# T123-3: guardrail_passed 검증
# ──────────────────────────────────────────────

class TestGuardrailFilter:
    """guardrail_passed=False인 응답은 캐시에 저장되지 않아야 한다."""

    def test_guardrail_failed_not_stored(self, cache):
        cache_id = cache.store(
            query="에러 코드 E001",
            model_id="770S",
            intent="troubleshoot",
            response="위험한 응답",
            guardrail_passed=False,
        )
        assert cache_id is None

    def test_guardrail_passed_stored(self, cache):
        cache_id = cache.store(
            query="에러 코드 E001",
            model_id="770S",
            intent="troubleshoot",
            response="안전한 응답",
            guardrail_passed=True,
        )
        assert cache_id is not None


# ──────────────────────────────────────────────
# T123-4: TTL 만료
# ──────────────────────────────────────────────

class TestTTLExpiration:
    """TTL이 만료된 캐시 엔트리가 자동 삭제되는지 검증한다."""

    def test_expired_entry_not_returned(self, cache):
        """생성 시간이 TTL을 초과하면 캐시 미스여야 한다."""
        cache_id = cache.store(
            query="프린터 연결 방법",
            model_id="770S",
            intent="connect",
            response="프린터 연결 절차는...",
        )
        assert cache_id is not None

        # created_at을 강제로 과거로 변경 (TTL 초과)
        meta = cache._collection.get(ids=[cache_id], include=["metadatas"])
        old_meta = meta["metadatas"][0]
        old_meta["created_at"] = int(time.time()) - 2000000  # ~23일 전 (connect TTL=14일)
        cache._collection.update(ids=[cache_id], metadatas=[old_meta])

        entry = cache.lookup(
            query="프린터 연결 방법",
            model_id="770S",
            threshold=0.0,
        )
        assert entry is None

    def test_non_expired_entry_returned(self, cache):
        """TTL 이내이면 캐시 히트여야 한다."""
        cache.store(
            query="설치 방법",
            model_id="270S",
            intent="install",
            response="270S 설치 절차는...",
        )
        entry = cache.lookup(query="설치 방법", model_id="270S", threshold=0.0)
        assert entry is not None


# ──────────────────────────────────────────────
# T123-5: invalidate
# ──────────────────────────────────────────────

class TestInvalidate:
    """캐시 무효화 동작 검증."""

    def test_invalidate_by_model(self, cache):
        cache.store(query="q1", model_id="770S", intent="install", response="r1")
        cache.store(query="q2", model_id="770S", intent="connect", response="r2")
        cache.store(query="q3", model_id="580", intent="install", response="r3")

        deleted = cache.invalidate(model_id="770S")
        assert deleted == 2

        # 770S 캐시 삭제 확인
        e1 = cache.lookup(query="q1", model_id="770S", threshold=0.0)
        assert e1 is None

        # 580 캐시 유지 확인
        e3 = cache.lookup(query="q3", model_id="580", threshold=0.0)
        assert e3 is not None

    def test_invalidate_by_model_and_intent(self, cache):
        cache.store(query="q1", model_id="770S", intent="install", response="r1")
        cache.store(query="q2", model_id="770S", intent="connect", response="r2")

        deleted = cache.invalidate(model_id="770S", intent="install")
        assert deleted == 1

        # install 삭제 확인 (threshold=0.5: 삭제된 벡터와 다른 벡터가 매칭되지 않도록)
        e1 = cache.lookup(query="q1", model_id="770S", threshold=0.5)
        assert e1 is None

        # connect 유지 확인
        e2 = cache.lookup(query="q2", model_id="770S", threshold=0.0)
        assert e2 is not None

    def test_invalidate_empty(self, cache):
        deleted = cache.invalidate(model_id="270S")
        assert deleted == 0


# ──────────────────────────────────────────────
# T123-6: get_stats
# ──────────────────────────────────────────────

class TestGetStats:
    """캐시 통계 조회 검증."""

    def test_empty_stats(self, cache):
        stats = cache.get_stats()
        assert stats["total_entries"] == 0
        assert stats["total_hits"] == 0
        assert stats["by_model"] == {}

    def test_stats_after_store(self, cache):
        cache.store(query="q1", model_id="770S", intent="install", response="r1")
        cache.store(query="q2", model_id="770S", intent="connect", response="r2")
        cache.store(query="q3", model_id="580", intent="install", response="r3")

        stats = cache.get_stats()
        assert stats["total_entries"] == 3
        assert stats["total_hits"] == 0
        assert "770S" in stats["by_model"]
        assert "580" in stats["by_model"]
        assert stats["by_model"]["770S"]["entries"] == 2
        assert stats["by_model"]["580"]["entries"] == 1

    def test_stats_after_hit(self, cache):
        cache.store(query="q1", model_id="770S", intent="install", response="r1")
        cache.lookup(query="q1", model_id="770S", threshold=0.0)

        stats = cache.get_stats()
        assert stats["total_hits"] == 1
        assert stats["by_model"]["770S"]["hits"] == 1


# ──────────────────────────────────────────────
# T123-7: cache disabled
# ──────────────────────────────────────────────

class TestCacheDisabled:
    """캐시 비활성화 시 동작 검증."""

    def test_store_returns_none_when_disabled(self, cache):
        with patch("src.cache.semantic_cache.settings") as mock_settings:
            mock_settings.enable_semantic_cache = False
            result = cache.store(
                query="q1", model_id="770S", intent="install", response="r1"
            )
            assert result is None

    def test_lookup_returns_none_when_disabled(self, cache):
        cache.store(query="q1", model_id="770S", intent="install", response="r1")
        with patch("src.cache.semantic_cache.settings") as mock_settings:
            mock_settings.enable_semantic_cache = False
            result = cache.lookup(query="q1", model_id="770S")
            assert result is None


# ──────────────────────────────────────────────
# T123-8: hit_count 증가
# ──────────────────────────────────────────────

class TestHitCounter:
    """캐시 히트 시 hit_count가 증가하는지 검증."""

    def test_hit_count_increments(self, cache):
        cache_id = cache.store(
            query="q1", model_id="770S", intent="install", response="r1"
        )

        # 3회 조회
        for _ in range(3):
            cache.lookup(query="q1", model_id="770S", threshold=0.0)

        meta = cache._collection.get(ids=[cache_id], include=["metadatas"])
        assert meta["metadatas"][0]["hit_count"] == 3


# ──────────────────────────────────────────────
# T123-9: image_urls 직렬화/역직렬화
# ──────────────────────────────────────────────

class TestImageUrls:
    """image_urls가 올바르게 저장/복원되는지 검증."""

    def test_image_urls_roundtrip(self, cache):
        urls = ["/static/images/770S/fig1.png", "/static/images/770S/fig2.png"]
        cache.store(
            query="설치 방법",
            model_id="770S",
            intent="install",
            response="설치 절차는...",
            image_urls=urls,
        )
        entry = cache.lookup(query="설치 방법", model_id="770S", threshold=0.0)
        assert entry is not None
        assert entry.image_urls == urls

    def test_empty_image_urls(self, cache):
        cache.store(
            query="설치 방법",
            model_id="770S",
            intent="install",
            response="설치 절차는...",
        )
        entry = cache.lookup(query="설치 방법", model_id="770S", threshold=0.0)
        assert entry is not None
        assert entry.image_urls == []
