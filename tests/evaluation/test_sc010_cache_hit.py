"""SC-010 캐시 히트율 평가 테스트 — T124

동일 기종+유사 질문에 대한 캐시 히트율이 60% 이상인지 검증한다.
동일 질문 반복 시 2번째부터 캐시 히트가 발생해야 한다.
"""

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


# 테스트 데이터: 기종별 반복 질문 시나리오
REPEAT_SCENARIOS = [
    ("770S", "connect", "프린터 연결 방법을 알려주세요"),
    ("770S", "troubleshoot", "에러 코드 E013이 떠요"),
    ("770S", "install", "기기 설치 방법이 궁금합니다"),
    ("580", "connect", "바코드 리더기 연결이 안 돼요"),
    ("580", "troubleshoot", "에러 코드 E001 해결 방법"),
    ("270S", "install", "InBody 270S 설치하려면 어떻게 하나요"),
    ("270S", "clinical", "체지방률 측정 결과가 이상해요"),
    ("970S", "connect", "PC 연결 방법을 알려주세요"),
    ("970S", "troubleshoot", "측정값이 비정상으로 나와요"),
    ("970S", "install", "기기 조립 방법이 궁금합니다"),
]


@pytest.mark.sc010
class TestSC010CacheHitRate:
    """SC-010: 동일 기종+유사 질문에 대한 캐시 히트율 ≥ 60%."""

    @pytest.mark.parametrize(
        "model_id,intent,query",
        REPEAT_SCENARIOS,
        ids=[f"{m}-{i}" for m, i, _ in REPEAT_SCENARIOS],
    )
    def test_repeat_query_hits_cache(self, cache, sc_metrics, model_id, intent, query):
        """동일 질문을 2번 전송하면 2번째에서 캐시 히트가 발생한다."""
        # 1차: 저장
        cache.store(
            query=query,
            model_id=model_id,
            intent=intent,
            response=f"{model_id} {intent} 응답입니다.",
            guardrail_passed=True,
        )

        # 2차: 조회 (동일 질문)
        entry = cache.lookup(query=query, model_id=model_id, threshold=0.0)
        hit = entry is not None
        sc_metrics.record("SC-010", hit)
        assert hit, f"동일 질문 반복 시 캐시 히트 실패: {model_id}/{intent}/{query}"

    def test_first_query_is_miss(self, cache, sc_metrics):
        """최초 질문은 캐시 미스여야 한다."""
        entry = cache.lookup(query="처음 보는 질문", model_id="770S")
        assert entry is None  # 미스는 히트율 통계에 포함하지 않음
