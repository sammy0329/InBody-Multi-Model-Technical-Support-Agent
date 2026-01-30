"""매뉴얼 RAG 검색 Tool — LangChain Tool Calling 용"""

from langchain_core.tools import tool

from src.rag.metadata import VALID_CATEGORIES, VALID_MODELS
from src.rag.vectorstore import get_retriever


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
        return f"매뉴얼 검색 중 오류가 발생했습니다: {e}"

    if not docs:
        return f"기종 {model} 매뉴얼에서 '{query}'에 대한 관련 정보를 찾지 못했습니다."

    lines = [f"기종 {model} 매뉴얼 검색 결과 ({len(docs)}건):"]
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source_file", "알 수 없음")
        page = doc.metadata.get("page_number", "?")
        lines.append(f"\n--- 결과 {i} (출처: {source}, 페이지: {page}) ---")
        lines.append(doc.page_content)

    return "\n".join(lines)
