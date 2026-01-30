"""구조화된 데이터 시딩 스크립트 — 에러 코드 및 주변기기 호환표 DB 로드"""

import asyncio
import logging
import sys
from pathlib import Path

# 프로젝트 루트를 PYTHONPATH에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.database import async_session_factory, engine, init_db
from src.db.seed import seed_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


async def main():
    """시드 데이터 로드 메인 함수"""
    print("=" * 50)
    print("InBody Tech-Master 구조화 데이터 시딩")
    print("=" * 50)

    print("\n1. DB 테이블 초기화 중...")
    await init_db()
    print("   → 완료")

    print("\n2. 시드 데이터 로드 중...")
    async with async_session_factory() as session:
        result = await seed_all(session)

    ec = result["error_codes"]
    pc = result["peripherals"]
    print(f"   → 에러 코드: {ec}건, 호환표: {pc}건")

    if ec == 0 and pc == 0:
        print("\n   (이미 데이터가 존재하여 건너뛰었습니다)")

    await engine.dispose()
    print("\n시딩 완료!")


if __name__ == "__main__":
    asyncio.run(main())
