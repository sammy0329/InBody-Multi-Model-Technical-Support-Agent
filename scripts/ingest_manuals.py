"""PDF 매뉴얼 인제스트 스크립트 — data/manuals/{기종}/ 디렉토리 순회"""

import logging
import sys
from pathlib import Path

# 프로젝트 루트를 PYTHONPATH에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.ingest import ingest_model_manuals
from src.rag.metadata import VALID_MODELS
from src.rag.vectorstore import add_documents_to_collection, init_collections

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """전체 기종 매뉴얼 인제스트 실행"""
    data_dir = Path(__file__).parent.parent / "data" / "manuals"

    print("=" * 50)
    print("InBody Tech-Master PDF 매뉴얼 인제스트")
    print("=" * 50)

    # 컬렉션 초기화
    print("\n1. Chroma 컬렉션 초기화 중...")
    init_collections()
    print("   → 4개 컬렉션 초기화 완료")

    # 기종별 인제스트
    print("\n2. 기종별 PDF 인제스트 중...")
    total = 0
    for model in sorted(VALID_MODELS):
        model_dir = data_dir / model
        if not model_dir.exists():
            print(f"   [{model}] 디렉토리 없음 — 건너뜀")
            continue

        chunks = ingest_model_manuals(model_dir, model)
        if not chunks:
            print(f"   [{model}] PDF 없음 — 건너뜀")
            continue

        count = add_documents_to_collection(model, chunks)
        total += count
        print(f"   [{model}] {count}개 청크 인제스트 완료")

    print(f"\n인제스트 완료: 총 {total}개 청크")


if __name__ == "__main__":
    main()
