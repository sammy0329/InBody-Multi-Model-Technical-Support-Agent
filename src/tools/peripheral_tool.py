"""주변기기 호환 조회 Tool — LangChain Tool Calling 용"""

from langchain_core.tools import tool
from sqlalchemy import select

from src.db.database import async_session_factory
from src.db.schemas import PeripheralCompatibilityTable


@tool
async def check_peripheral_compatibility(
    model: str,
    peripheral_type: str = "",
    peripheral_name: str = "",
) -> str:
    """기종의 주변기기 호환 여부를 확인합니다.

    Args:
        model: InBody 기종 (270S, 580, 770S, 970S)
        peripheral_type: 주변기기 유형 (printer, pc, barcode_reader, usb 등, 빈 문자열이면 전체)
        peripheral_name: 주변기기 이름 (빈 문자열이면 해당 유형 전체)

    Returns:
        호환 정보 및 연결 방법
    """
    async with async_session_factory() as session:
        query = select(PeripheralCompatibilityTable).where(
            PeripheralCompatibilityTable.model_id == model
        )

        if peripheral_type:
            query = query.where(
                PeripheralCompatibilityTable.peripheral_type == peripheral_type
            )
        if peripheral_name:
            query = query.where(
                PeripheralCompatibilityTable.peripheral_name.ilike(
                    f"%{peripheral_name}%"
                )
            )

        result = await session.execute(query)
        rows = result.scalars().all()

    if not rows:
        filters = f"기종={model}"
        if peripheral_type:
            filters += f", 유형={peripheral_type}"
        if peripheral_name:
            filters += f", 이름={peripheral_name}"
        return f"조건에 맞는 호환 정보가 없습니다 ({filters})."

    lines = [f"기종 {model}의 주변기기 호환 정보:"]
    for row in rows:
        status = "✅ 호환" if row.is_compatible else "❌ 비호환"
        lines.append(f"\n[{row.peripheral_type}] {row.peripheral_name}: {status}")
        if row.connection_method:
            lines.append(f"  연결 방식: {row.connection_method}")
        if row.setup_steps:
            lines.append("  설정 절차:")
            for i, step in enumerate(row.setup_steps, 1):
                lines.append(f"    {i}. {step}")

    return "\n".join(lines)
