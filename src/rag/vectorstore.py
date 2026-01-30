"""벡터 DB 초기화 및 기종별 리트리버 팩토리 — 기종 격리 Layer 1+2 구현"""

import logging
from pathlib import Path

import chromadb
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

from src.config import settings
from src.rag.metadata import (
    VALID_MODELS,
    build_model_category_filter,
    build_model_filter,
)

logger = logging.getLogger(__name__)

# 기종별 컬렉션명 매핑 (Layer 1: 물리적 격리)
COLLECTION_NAMES = {model: f"inbody_{model.lower()}" for model in VALID_MODELS}

# 임베딩 모델 싱글톤
_embeddings: OpenAIEmbeddings | None = None


def get_embeddings() -> OpenAIEmbeddings:
    """OpenAI 임베딩 모델 싱글톤 반환"""
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(openai_api_key=settings.openai_api_key)
    return _embeddings


def get_chroma_client() -> chromadb.ClientAPI:
    """Chroma 영속 클라이언트 반환"""
    persist_dir = Path(settings.chroma_persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(persist_dir))


def init_collections() -> dict[str, Chroma]:
    """기종별 Chroma 컬렉션 초기화 (4개)"""
    client = get_chroma_client()
    embeddings = get_embeddings()
    collections = {}

    for model, collection_name in COLLECTION_NAMES.items():
        collections[model] = Chroma(
            client=client,
            collection_name=collection_name,
            embedding_function=embeddings,
        )
        logger.info("컬렉션 초기화: %s (%s)", collection_name, model)

    return collections


def add_documents_to_collection(
    model: str,
    chunks: list[dict],
) -> int:
    """청크 리스트를 해당 기종 컬렉션에 추가"""
    if model not in VALID_MODELS:
        raise ValueError(f"지원하지 않는 기종: {model}")

    client = get_chroma_client()
    embeddings = get_embeddings()
    collection_name = COLLECTION_NAMES[model]

    vectorstore = Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embeddings,
    )

    texts = [chunk["text"] for chunk in chunks]
    metadatas = [chunk["metadata"] for chunk in chunks]

    vectorstore.add_texts(texts=texts, metadatas=metadatas)
    logger.info("컬렉션 %s에 %d개 문서 추가", collection_name, len(texts))
    return len(texts)


def get_retriever(
    model: str,
    category: str | None = None,
    k: int = 5,
):
    """기종별 리트리버 반환 — 메타데이터 필터 필수 적용 (Layer 2: 논리적 격리)

    Args:
        model: InBody 기종 (270S, 580, 770S, 970S)
        category: 카테고리 필터 (선택)
        k: 검색 결과 수
    """
    if model not in VALID_MODELS:
        raise ValueError(f"지원하지 않는 기종: {model}")

    client = get_chroma_client()
    embeddings = get_embeddings()
    collection_name = COLLECTION_NAMES[model]

    vectorstore = Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embeddings,
    )

    # Layer 2: 기종 필터 필수 + 카테고리 필터 선택
    if category:
        search_filter = build_model_category_filter(model, category)
    else:
        search_filter = build_model_filter(model)

    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k, "filter": search_filter},
    )
