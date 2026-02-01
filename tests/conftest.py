"""공통 테스트 픽스처 + SC 메트릭 수집기"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.db.schemas import Base


# ──────────────────────────────────────────────
# SC 메트릭 수집기
# ──────────────────────────────────────────────

SC_TARGETS = {
    "SC-001": {"label": "기종 식별 정확도", "target": 95.0, "direction": ">="},
    "SC-003": {"label": "에러코드 해결 정확도", "target": 90.0, "direction": ">="},
    "SC-004": {"label": "면책 문구 삽입률", "target": 100.0, "direction": "="},
    "SC-005": {"label": "기종 간 정보 격리", "target": 100.0, "direction": "="},
    "SC-006": {"label": "Level 3 안전 차단율", "target": 100.0, "direction": "="},
    "SC-009": {"label": "할루시네이션 방지율", "target": 100.0, "direction": "="},
    "SC-010": {"label": "캐시 히트율", "target": 60.0, "direction": ">="},
    "SC-011": {"label": "캐시 응답 지연", "target": 100.0, "direction": "="},
    "SC-012": {"label": "캐시 교차 오염", "target": 100.0, "direction": "="},
}


class SCMetricsCollector:
    """SC 성공 기준별 pass/fail 결과를 누적한다."""

    def __init__(self):
        self.results: dict[str, list[bool]] = {sc: [] for sc in SC_TARGETS}

    def record(self, sc_id: str, passed: bool):
        if sc_id in self.results:
            self.results[sc_id].append(passed)

    def summary(self) -> dict[str, dict]:
        report = {}
        for sc_id, outcomes in self.results.items():
            total = len(outcomes)
            passed = sum(outcomes)
            rate = (passed / total * 100) if total > 0 else 0.0
            target = SC_TARGETS[sc_id]["target"]
            direction = SC_TARGETS[sc_id]["direction"]

            if direction == ">=":
                met = rate >= target
            else:
                met = rate == target

            report[sc_id] = {
                "label": SC_TARGETS[sc_id]["label"],
                "total": total,
                "passed": passed,
                "rate": rate,
                "target": f"{direction}{target:.0f}%",
                "met": met,
            }
        return report


_collector = SCMetricsCollector()


@pytest.fixture(scope="session")
def sc_metrics():
    """세션 전체에서 공유되는 SC 메트릭 수집기"""
    return _collector


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """테스트 세션 종료 후 SC 메트릭 리포트를 출력한다."""
    report = _collector.summary()
    has_data = any(r["total"] > 0 for r in report.values())
    if not has_data:
        return

    terminalreporter.write_sep("=", "InBody Tech-Master SC Metrics Report")
    for sc_id, data in report.items():
        if data["total"] == 0:
            continue
        status = "PASS ✅" if data["met"] else "FAIL ❌"
        terminalreporter.write_line(
            f"  {sc_id} | {data['label']:<16s} | "
            f"{data['passed']:>3d}/{data['total']:<3d} | "
            f"{data['rate']:>6.1f}% | "
            f"Target: {data['target']:<6s} | {status}"
        )
    terminalreporter.write_sep("=", "")


# ──────────────────────────────────────────────
# 기존 테스트 픽스처
# ──────────────────────────────────────────────


@pytest.fixture
async def async_engine():
    """인메모리 SQLite 비동기 엔진"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(async_engine):
    """테스트용 DB 세션"""
    async_session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture
async def client():
    """테스트용 FastAPI 클라이언트"""
    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
