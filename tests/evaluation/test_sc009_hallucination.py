"""SC-009 평가: 미등록 에러 코드 할루시네이션 방지율 = 0%

시드 DB에 없는 에러 코드 조회 시 '찾을 수 없습니다'를 반환하고,
등록된 에러 코드는 정상 조회되는지 측정한다.
"""

from unittest.mock import patch

import pytest

from src.tools.error_code_tool import lookup_error_code

# 미등록 에러 코드 (시드 데이터에 없는 코드)
SC009_UNKNOWN_CASES = [
    ("270S", "E099"),
    ("270S", "E050"),
    ("270S", "E999"),
    ("580", "E099"),
    ("580", "E050"),
    ("580", "E999"),
    ("770S", "E099"),
    ("770S", "E050"),
    ("770S", "E999"),
    ("970S", "E099"),
    ("970S", "E050"),
    ("970S", "E999"),
]

# 등록된 에러 코드 (시드 데이터에 존재하는 코드)
SC009_REGISTERED_CASES = [
    ("270S", "E001"),
    ("270S", "E002"),
    ("270S", "E003"),
    ("580", "E001"),
    ("580", "E004"),
    ("770S", "E001"),
    ("770S", "E006"),
    ("970S", "E001"),
    ("970S", "E013"),
]


@pytest.mark.evaluation
@pytest.mark.sc009
@pytest.mark.parametrize(
    "model_id, error_code",
    SC009_UNKNOWN_CASES,
    ids=[f"sc009_unknown_{m}_{c}" for m, c in SC009_UNKNOWN_CASES],
)
async def test_sc009_unknown_code_rejected(model_id, error_code, seeded_session_factory, sc_metrics):
    """SC-009: 미등록 에러 코드는 '찾을 수 없습니다'를 반환하고 해결책을 생성하지 않는다."""
    with patch("src.tools.error_code_tool.async_session_factory", seeded_session_factory):
        result = await lookup_error_code.ainvoke({
            "model": model_id,
            "error_code": error_code,
        })

    not_found = "찾을 수 없습니다" in result
    no_hallucination = "해결 단계" not in result

    passed = not_found and no_hallucination
    sc_metrics.record("SC-009", passed)
    assert passed, (
        f"model={model_id}, code={error_code}: "
        f"not_found={not_found}, no_hallucination={no_hallucination}, "
        f"result={result[:100]}..."
    )


@pytest.mark.evaluation
@pytest.mark.sc009
@pytest.mark.parametrize(
    "model_id, error_code",
    SC009_REGISTERED_CASES,
    ids=[f"sc009_registered_{m}_{c}" for m, c in SC009_REGISTERED_CASES],
)
async def test_sc009_registered_code_found(model_id, error_code, seeded_session_factory, sc_metrics):
    """SC-009: 등록된 에러 코드는 정상적으로 조회되어 해결 단계를 포함한다."""
    with patch("src.tools.error_code_tool.async_session_factory", seeded_session_factory):
        result = await lookup_error_code.ainvoke({
            "model": model_id,
            "error_code": error_code,
        })

    found = "찾을 수 없습니다" not in result
    has_steps = "해결 단계" in result

    passed = found and has_steps
    sc_metrics.record("SC-009", passed)
    assert passed, (
        f"model={model_id}, code={error_code}: "
        f"found={found}, has_steps={has_steps}, "
        f"result={result[:100]}..."
    )
