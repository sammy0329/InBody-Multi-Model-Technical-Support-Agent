"""에러 코드 조회 Tool — LangChain Tool Calling 용"""

from langchain_core.tools import tool
from sqlalchemy import select

from src.db.database import async_session_factory
from src.db.schemas import ErrorCodeTable
from src.models.error_codes import ErrorCodeResponse


@tool
async def lookup_error_code(model: str, error_code: str) -> str:
    """특정 기종의 에러 코드를 조회합니다.

    Args:
        model: InBody 기종 (270S, 580, 770S, 970S)
        error_code: 조회할 에러 코드 (예: E001)

    Returns:
        에러 코드 정보 (원인, 해결 방법, 지원 수준)
    """
    async with async_session_factory() as session:
        result = await session.execute(
            select(ErrorCodeTable).where(
                ErrorCodeTable.model_id == model,
                ErrorCodeTable.code == error_code,
            )
        )
        row = result.scalar_one_or_none()

    if row is None:
        return f"기종 {model}에서 에러 코드 '{error_code}'을(를) 찾을 수 없습니다."

    response = ErrorCodeResponse(
        code=row.code,
        model_id=row.model_id,
        title=row.title,
        description=row.description,
        cause=row.cause,
        support_level=row.support_level,
        resolution_steps=row.resolution_steps,
        escalation_note=row.escalation_note,
    )

    level_text = (
        "사용자 해결 가능 (Level 1)"
        if response.support_level == "level_1"
        else "서비스 센터 이관 필요 (Level 3)"
    )
    steps = "\n".join(
        f"  {i + 1}. {step}" for i, step in enumerate(response.resolution_steps)
    )

    result_text = (
        f"에러 코드: {response.code}\n"
        f"제목: {response.title}\n"
        f"원인: {response.cause}\n"
        f"지원 수준: {level_text}\n"
        f"해결 단계:\n{steps}"
    )

    if response.escalation_note:
        result_text += f"\n참고: {response.escalation_note}"

    return result_text


@tool
async def search_errors_by_symptom(model: str, symptom_description: str) -> str:
    """증상 설명으로 관련 에러 코드를 검색합니다.

    Args:
        model: InBody 기종 (270S, 580, 770S, 970S)
        symptom_description: 증상 설명 (예: "화면이 안 켜져요", "측정값이 이상해요")

    Returns:
        관련 에러 코드 목록
    """
    async with async_session_factory() as session:
        result = await session.execute(
            select(ErrorCodeTable).where(ErrorCodeTable.model_id == model)
        )
        rows = result.scalars().all()

    if not rows:
        return f"기종 {model}에 등록된 에러 코드가 없습니다."

    # 증상 키워드 기반 매칭
    keyword = symptom_description.lower()
    matched = [
        row
        for row in rows
        if keyword in row.description.lower()
        or keyword in row.cause.lower()
        or keyword in row.title.lower()
    ]

    if not matched:
        matched = rows
        header = (
            f"기종 {model}의 전체 에러 코드 목록 "
            f"(증상 '{symptom_description}'과 정확히 일치하는 항목 없음):"
        )
    else:
        header = f"기종 {model}에서 '{symptom_description}' 관련 에러 코드:"

    lines = [header]
    for row in matched:
        level = "L1" if row.support_level == "level_1" else "L3"
        lines.append(f"  - [{level}] {row.code}: {row.title} — {row.cause}")

    return "\n".join(lines)
