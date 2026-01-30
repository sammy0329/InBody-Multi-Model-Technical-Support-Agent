"""메타데이터 태깅 및 필터 유틸리티 — 기종 격리의 핵심"""

VALID_MODELS = {"270S", "580", "770S", "970S"}
VALID_CATEGORIES = {"installation", "connection", "troubleshooting", "clinical", "general"}


def create_metadata(
    model: str,
    category: str = "general",
    section_hierarchy: str = "",
    source_file: str = "",
    page_number: int = 0,
) -> dict:
    """RAG 문서용 메타데이터 딕셔너리 생성

    Args:
        model: InBody 기종 (270S, 580, 770S, 970S)
        category: 문서 카테고리
        section_hierarchy: 문서 내 섹션 경로
        source_file: 원본 파일명
        page_number: 원본 페이지 번호
    """
    if model not in VALID_MODELS:
        raise ValueError(f"지원하지 않는 기종: {model}. 지원 기종: {VALID_MODELS}")
    if category not in VALID_CATEGORIES:
        raise ValueError(f"지원하지 않는 카테고리: {category}. 지원: {VALID_CATEGORIES}")

    return {
        "model": model,
        "category": category,
        "section_hierarchy": section_hierarchy,
        "source_file": source_file,
        "page_number": page_number,
    }


def build_model_filter(model: str) -> dict:
    """기종별 메타데이터 필터 생성 (Chroma where 조건)"""
    if model not in VALID_MODELS:
        raise ValueError(f"지원하지 않는 기종: {model}")
    return {"model": model}


def build_model_category_filter(model: str, category: str) -> dict:
    """기종 + 카테고리 복합 필터 생성"""
    if model not in VALID_MODELS:
        raise ValueError(f"지원하지 않는 기종: {model}")
    if category not in VALID_CATEGORIES:
        raise ValueError(f"지원하지 않는 카테고리: {category}")
    return {"$and": [{"model": model}, {"category": category}]}
