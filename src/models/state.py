"""LangGraph 에이전트 상태 정의"""

from typing import TypedDict

from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """멀티 에이전트 워크플로우 공유 상태

    LangGraph의 각 노드가 읽고 쓰는 공유 상태 딕셔너리.
    기종 식별 → 의도 분류 → 전문 에이전트 → 가드레일 흐름에서 사용된다.
    """

    # 대화 이력
    messages: list[BaseMessage]

    # 기종 식별 결과
    identified_model: str | None  # "270S" | "580" | "770S" | "970S" | None
    model_tier: str | None  # "entry" | "professional"

    # 의도 분류 결과
    intent: str | None  # "install" | "connect" | "troubleshoot" | "clinical" | "general"

    # RAG 검색 결과
    retrieved_docs: list[str]

    # 에러 코드 관련
    error_code: str | None
    support_level: str | None  # "level_1" | "level_3"

    # 톤앤매너
    tone_profile: str | None  # "casual" | "professional"

    # 안전 검증
    needs_disclaimer: bool
    answer: str | None
    guardrail_passed: bool | None
