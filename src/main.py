"""FastAPI 앱 진입점 — T037"""

import logging
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 DB 초기화/정리"""
    logging.basicConfig(level=settings.log_level)
    logger = logging.getLogger(__name__)

    # 시작: DB 테이블 생성
    try:
        from src.db.database import init_db

        await init_db()
        logger.info("DB 초기화 완료")
    except Exception:
        logger.exception("DB 초기화 실패")

    yield

    # 종료: DB 엔진 정리
    try:
        from src.db.database import engine

        await engine.dispose()
        logger.info("DB 연결 종료")
    except Exception:
        logger.exception("DB 종료 실패")


app = FastAPI(
    title="InBody Tech-Master",
    description="InBody 기종 식별 기반 멀티 에이전트 기술 지원 시스템",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
from src.api.chat import router as chat_router  # noqa: E402
from src.api.errors import router as errors_router  # noqa: E402
from src.api.health import router as health_router  # noqa: E402

app.include_router(chat_router)
app.include_router(errors_router)
app.include_router(health_router)

# 정적 파일 서빙 (이미지 등)
_static_dir = Path(__file__).parent.parent / "static"
_static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")
