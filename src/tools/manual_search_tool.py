"""매뉴얼 RAG 검색 Tool — LangChain Tool Calling 용"""

import logging
import re

from langchain_core.tools import tool

from src.prompts.disclaimers import SERVICE_CENTER_INFO
from src.rag.metadata import VALID_CATEGORIES, VALID_MODELS
from src.rag.vectorstore import get_retriever

logger = logging.getLogger(__name__)


@tool
def search_manual(model: str, query: str, category: str = "") -> str:
    """기종별 매뉴얼에서 관련 정보를 검색합니다.

    Args:
        model: InBody 기종 (270S, 580, 770S, 970S)
        query: 검색 질의
        category: 카테고리 필터 (installation, connection, troubleshooting,
                  clinical, general, 빈 문자열이면 전체)

    Returns:
        매뉴얼에서 검색된 관련 문서 내용
    """
    if model not in VALID_MODELS:
        return (
            f"지원하지 않는 기종입니다: {model}. "
            f"지원 기종: {', '.join(sorted(VALID_MODELS))}"
        )

    cat = category if category and category in VALID_CATEGORIES else None

    try:
        retriever = get_retriever(model=model, category=cat, k=5)
        docs = retriever.invoke(query)
    except Exception as e:
        logger.warning("매뉴얼 검색 오류 (model=%s, category=%s): %s", model, cat, e)
        docs = []

    # Level 1 폴백: 카테고리 필터 제거 후 재검색
    if not docs and cat:
        logger.info("카테고리 필터 '%s' 제거 후 재검색 (model=%s)", cat, model)
        try:
            retriever = get_retriever(model=model, category=None, k=5)
            docs = retriever.invoke(query)
        except Exception as e:
            logger.warning("폴백 검색 오류 (model=%s): %s", model, e)
            docs = []

    # Level 2 폴백: 구조화된 실패 메시지
    if not docs:
        return (
            f"기종 {model} 매뉴얼에서 '{query}'에 대한 관련 정보를 "
            f"찾지 못했습니다.\n\n"
            f"다음 방법을 시도해 보세요:\n"
            f"- 다른 키워드로 다시 질문해 주세요\n"
            f"- 구체적인 증상이나 에러 코드를 알려주세요\n\n"
            f"추가 도움이 필요하시면 InBody 고객센터로 문의해 주세요.\n"
            f"{SERVICE_CENTER_INFO}"
        )

    lines = [f"기종 {model} 매뉴얼 검색 결과 ({len(docs)}건):"]
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source_file", "알 수 없음")
        page = doc.metadata.get("page_number", "?")
        content_type = doc.metadata.get("content_type", "text")
        image_url = doc.metadata.get("image_url", "")

        header = f"\n--- 결과 {i} (출처: {source}, 페이지: {page}"
        if content_type == "image" and image_url:
            header += f", 이미지: {image_url}"
        header += ") ---"

        lines.append(header)
        lines.append(doc.page_content)

    return "\n".join(lines)


def extract_image_urls(search_result: str) -> list[str]:
    """search_manual 결과 텍스트에서 이미지 URL 목록을 추출한다."""
    return re.findall(r"이미지: (/static/images/[^)]+)", search_result)
