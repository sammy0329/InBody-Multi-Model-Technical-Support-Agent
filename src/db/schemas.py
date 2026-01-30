"""SQLAlchemy ORM 테이블 정의 — 에러 코드 및 주변기기 호환표"""

from sqlalchemy import Boolean, Column, Integer, JSON, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy 선언적 베이스"""
    pass


class ErrorCodeTable(Base):
    """에러 코드 테이블 — 기종별 에러 코드 및 해결 정보"""

    __tablename__ = "error_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, index=True)
    model_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    cause = Column(String, nullable=False)
    support_level = Column(String, nullable=False)  # "level_1" | "level_3"
    resolution_steps = Column(JSON, nullable=False)  # list[str]
    escalation_note = Column(String, nullable=True)


class PeripheralCompatibilityTable(Base):
    """주변기기 호환표 테이블 — 기종별 주변기기 호환 정보"""

    __tablename__ = "peripheral_compatibility"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String, nullable=False, index=True)
    peripheral_type = Column(String, nullable=False, index=True)
    peripheral_name = Column(String, nullable=False)
    is_compatible = Column(Boolean, nullable=False, default=True)
    connection_method = Column(String, nullable=True)
    setup_steps = Column(JSON, nullable=False)  # list[str]
