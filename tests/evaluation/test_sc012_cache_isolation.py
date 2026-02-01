"""SC-012 캐시 교차 오염 평가 테스트 — T126

캐시된 응답이 다른 기종의 정보를 포함하는 교차 오염 발생률이 0%인지 검증한다.
동일한 질문을 여러 기종에 대해 저장한 후, 기종 필터가 정확히 동작하는지 확인한다.
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


MODELS = ["270S", "580", "770S", "970S"]
INTENTS = ["install", "connect", "troubleshoot", "clinical"]

# 기종 격리 테스트: 동일한 질문을 여러 기종에 저장
SHARED_QUERIES = {
    "install": "설치 방법을 알려주세요",
    "connect": "프린터 연결 방법",
    "troubleshoot": "에러 코드 E001 해결",
    "clinical": "체지방률 의미가 뭔가요",
}


def _seed_shared_queries(cache):
    """동일한 질문을 4개 기종에 각각 저장한다 (기종별 응답은 다름)."""
    for model_id in MODELS:
        for intent, query in SHARED_QUERIES.items():
            cache.store(
                query=query,
                model_id=model_id,
                intent=intent,
                response=f"InBody {model_id} {intent} 전용 응답입니다.",
                guardrail_passed=True,
            )


@pytest.mark.sc012
class TestSC012CacheIsolation:
    """SC-012: 캐시 교차 오염 발생률 0%."""

    @pytest.mark.parametrize("target_model", MODELS)
    def test_cache_hit_returns_correct_model(self, cache, sc_metrics, target_model):
        """동일 질문을 모든 기종에 저장 후, 특정 기종 조회 시 해당 기종 응답만 반환."""
        _seed_shared_queries(cache)

        for intent, query in SHARED_QUERIES.items():
            entry = cache.lookup(query=query, model_id=target_model, threshold=0.0)
            correct = (
                entry is not None
                and entry.identified_model == target_model
                and f"InBody {target_model}" in entry.response
            )
            sc_metrics.record("SC-012", correct)
            assert correct, (
                f"기종 격리 실패: {target_model}/{intent} 조회 시 "
                f"다른 기종 응답 반환 (got: {entry.response if entry else 'None'})"
            )

    @pytest.mark.parametrize("target_model", MODELS)
    def test_no_other_model_response(self, cache, sc_metrics, target_model):
        """캐시 히트 응답에 다른 기종 정보가 포함되지 않아야 한다."""
        _seed_shared_queries(cache)

        other_models = [m for m in MODELS if m != target_model]
        for intent, query in SHARED_QUERIES.items():
            entry = cache.lookup(query=query, model_id=target_model, threshold=0.0)
            if entry is None:
                sc_metrics.record("SC-012", False)
                pytest.fail(f"캐시 히트 실패: {target_model}/{intent}")
                continue

            # 응답에 다른 기종명이 포함되지 않는지 확인
            for other in other_models:
                no_contamination = f"InBody {other}" not in entry.response
                sc_metrics.record("SC-012", no_contamination)
                assert no_contamination, (
                    f"교차 오염: {target_model} 응답에 {other} 정보 포함"
                )

    def test_single_model_store_not_returned_for_other(self, cache, sc_metrics):
        """한 기종에만 저장된 캐시가 다른 기종 조회에서 반환되지 않아야 한다."""
        # 770S에만 저장
        cache.store(
            query="고유한 질문입니다",
            model_id="770S",
            intent="install",
            response="770S 전용 응답",
            guardrail_passed=True,
        )

        # 다른 기종으로 조회 — 해당 기종에 엔트리가 없으므로 미스
        for other in ["270S", "580", "970S"]:
            entry = cache.lookup(query="고유한 질문입니다", model_id=other, threshold=0.0)
            no_contamination = entry is None
            sc_metrics.record("SC-012", no_contamination)
            assert no_contamination, (
                f"교차 오염: 770S 전용 캐시가 {other} 조회에서 반환됨"
            )

    def test_invalidate_one_model_does_not_affect_others(self, cache, sc_metrics):
        """한 기종의 캐시 무효화가 다른 기종에 영향을 주지 않아야 한다."""
        _seed_shared_queries(cache)

        # 770S 캐시만 삭제
        cache.invalidate(model_id="770S")

        # 770S 캐시 삭제 확인
        for intent, query in SHARED_QUERIES.items():
            entry = cache.lookup(query=query, model_id="770S", threshold=0.0)
            assert entry is None, "770S 캐시가 삭제되지 않음"

        # 나머지 기종 캐시 유지 확인
        for model_id in ["270S", "580", "970S"]:
            for intent, query in SHARED_QUERIES.items():
                entry = cache.lookup(query=query, model_id=model_id, threshold=0.0)
                preserved = entry is not None
                sc_metrics.record("SC-012", preserved)
                assert preserved, (
                    f"770S 삭제 시 {model_id}/{intent} 캐시도 사라짐"
                )
