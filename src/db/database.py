"""SQLAlchemy 비동기 엔진 및 세션 팩토리"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.config import settings

# 비동기 엔진 — SQLite(개발) / PostgreSQL(프로덕션) 자동 전환
engine = create_async_engine(settings.structured_db_url, echo=False)

# 세션 팩토리
async_session_factory = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session():
    """FastAPI Depends 용 DB 세션 제너레이터"""
    async with async_session_factory() as session:
        yield session


async def init_db():
    """DB 테이블 초기화 — 앱 시작 시 호출"""
    from src.db.schemas import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
