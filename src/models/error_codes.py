"""에러 코드 데이터 모델 — Pydantic 응답 스키마"""

from pydantic import BaseModel


class ErrorCodeResponse(BaseModel):
    """에러 코드 조회 응답 스키마"""

    code: str
    model_id: str
    title: str
    description: str
    cause: str
    support_level: str  # "level_1" | "level_3"
    resolution_steps: list[str]
    escalation_note: str | None = None
