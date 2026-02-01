"""SC-011 캐시 응답 지연 평가 테스트 — T125

캐시 히트 시 응답 지연이 200ms 이하인지 검증한다.
인메모리 Chroma + mock embeddings 사용으로 네트워크 지연 없음.
"""

import time
from unittest.mock import patch

import chromadb
import pytest


class FakeEmbeddings:
    """동일 문자열 → 동일 벡터를 반환하는 가짜 임베딩."""

    def __init__(self):
        self._cache: dict[str, list[float]] = {}
        self._counter = 0

    def embed_query(self, text: str) -> list[float]:
        if text not in self._cache:
            vec = [0.0] * 128
            vec[self._counter % 128] = 1.0
            self._cache[text] = vec
            self._counter += 1
        return self._cache[text]


@pytest.fixture
def cache():
    from src.cache.semantic_cache import SemanticCache

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

        try:
            client.delete_collection("semantic_cache")
        except Exception:
            pass


LATENCY_LIMIT_MS = 200

# 캐시 응답 지연 테스트 시나리오
LATENCY_SCENARIOS = [
    ("770S", "connect", "프린터 연결 방법", "프린터 연결 절차는 다음과 같습니다..."),
    ("770S", "troubleshoot", "에러 코드 E013", "E013 에러는 전극 접촉 불량으로 발생합니다..."),
    ("580", "install", "기기 설치 방법", "InBody 580 설치 절차: 1단계..."),
    ("270S", "clinical", "체지방률 의미", "체지방률은 체내 지방의 비율을 의미합니다..."),
    ("970S", "connect", "PC 연결 방법", "PC 연결은 USB 케이블을 사용합니다..."),
    # 긴 응답도 200ms 이내여야 함
    ("770S", "install", "설치 전체 절차", "A" * 5000),
    ("580", "troubleshoot", "에러 E001", "B" * 5000),
    ("270S", "connect", "바코드 리더기", "C" * 3000),
]


@pytest.mark.sc011
class TestSC011CacheLatency:
    """SC-011: 캐시 히트 시 응답 지연 ≤ 200ms."""

    @pytest.mark.parametrize(
        "model_id,intent,query,response",
        LATENCY_SCENARIOS,
        ids=[f"{m}-{i}" for m, i, _, _ in LATENCY_SCENARIOS],
    )
    def test_cache_hit_latency(self, cache, sc_metrics, model_id, intent, query, response):
        """캐시 히트의 lookup 시간이 200ms 이내여야 한다."""
        # 저장
        cache.store(
            query=query,
            model_id=model_id,
            intent=intent,
            response=response,
            guardrail_passed=True,
        )

        # 조회 시간 측정
        start = time.perf_counter()
        entry = cache.lookup(query=query, model_id=model_id, threshold=0.0)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert entry is not None, "캐시 히트 실패"
        within_limit = elapsed_ms <= LATENCY_LIMIT_MS
        sc_metrics.record("SC-011", within_limit)
        assert within_limit, (
            f"캐시 지연 초과: {elapsed_ms:.1f}ms > {LATENCY_LIMIT_MS}ms "
            f"(model={model_id}, intent={intent})"
        )
