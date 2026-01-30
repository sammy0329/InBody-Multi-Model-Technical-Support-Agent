"""주변기기 호환 데이터 모델 — Pydantic 응답 스키마"""

from pydantic import BaseModel


class PeripheralCompatibilityResponse(BaseModel):
    """주변기기 호환 조회 응답 스키마"""

    model_id: str
    peripheral_type: str  # "printer" | "pc" | "barcode_reader" | "usb"
    peripheral_name: str
    is_compatible: bool
    connection_method: str | None = None
    setup_steps: list[str] = []
