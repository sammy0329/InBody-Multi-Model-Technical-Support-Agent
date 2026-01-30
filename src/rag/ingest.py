"""PDF 매뉴얼 인제스트 — 청킹 + 기종별 메타데이터 태깅"""

import logging
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.rag.metadata import create_metadata

logger = logging.getLogger(__name__)

# 청킹 설정: 512토큰 ≈ 1024자(한국어 기준), 20% 오버랩
TEXT_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=1024,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def load_and_chunk_pdf(
    pdf_path: str | Path,
    model: str,
    category: str = "general",
) -> list[dict]:
    """PDF 파일을 로드하고 청킹하여 메타데이터가 태깅된 문서 리스트 반환

    Args:
        pdf_path: PDF 파일 경로
        model: InBody 기종 (270S, 580, 770S, 970S)
        category: 문서 카테고리

    Returns:
        [{"text": "...", "metadata": {...}}, ...] 형태의 청크 리스트
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")

    logger.info("PDF 로드 중: %s (기종: %s)", pdf_path.name, model)
    loader = PyPDFLoader(str(pdf_path))
    pages = loader.load()

    chunks = []
    for page in pages:
        page_num = page.metadata.get("page", 0)
        page_chunks = TEXT_SPLITTER.split_text(page.page_content)
        for chunk_text in page_chunks:
            if not chunk_text.strip():
                continue
            metadata = create_metadata(
                model=model,
                category=category,
                source_file=pdf_path.name,
                page_number=page_num,
            )
            chunks.append({"text": chunk_text, "metadata": metadata})

    logger.info("텍스트 청킹 완료: %s → %d개 청크", pdf_path.name, len(chunks))
    return chunks


def ingest_model_manuals(
    manuals_dir: str | Path,
    model: str,
) -> list[dict]:
    """특정 기종의 매뉴얼 디렉토리 내 모든 PDF를 인제스트"""
    manuals_dir = Path(manuals_dir)
    if not manuals_dir.exists():
        logger.warning("매뉴얼 디렉토리가 없습니다: %s", manuals_dir)
        return []

    all_chunks = []
    pdf_files = sorted(manuals_dir.glob("*.pdf"))

    if not pdf_files:
        logger.warning("PDF 파일이 없습니다: %s", manuals_dir)
        return []

    for pdf_path in pdf_files:
        chunks = load_and_chunk_pdf(pdf_path, model=model)
        all_chunks.extend(chunks)

    logger.info("기종 %s 인제스트 완료: 총 %d개 청크", model, len(all_chunks))
    return all_chunks
