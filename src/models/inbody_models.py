"""InBody 기종 프로필 상수 정의"""

from dataclasses import dataclass, field


SUPPORTED_MODELS = {"270S", "580", "770S", "970S"}


@dataclass(frozen=True)
class InBodyModelProfile:
    """InBody 기종별 프로필 — 기종 식별 후 톤앤매너·설치 유형 등을 결정하는 데 사용"""

    model_id: str
    name: str
    tier: str  # "entry" | "professional"
    install_type: str  # "foldable" | "separable"
    tone_profile: str  # "casual" | "professional"
    measurement_items: tuple[str, ...] = field(default_factory=tuple)
    description: str = ""


# 기종별 프로필 상수
INBODY_MODELS: dict[str, InBodyModelProfile] = {
    "270S": InBodyModelProfile(
        model_id="270S",
        name="InBody 270S",
        tier="entry",
        install_type="foldable",
        tone_profile="casual",
        measurement_items=(
            "체중", "골격근량", "체지방량", "BMI", "체지방률",
        ),
        description="피트니스 센터 및 소규모 클리닉용 보급형 체성분 분석기",
    ),
    "580": InBodyModelProfile(
        model_id="580",
        name="InBody 580",
        tier="entry",
        install_type="foldable",
        tone_profile="casual",
        measurement_items=(
            "체중", "골격근량", "체지방량", "BMI", "체지방률",
            "내장지방레벨", "기초대사량",
        ),
        description="기업 건강관리 및 체육시설용 보급형 체성분 분석기",
    ),
    "770S": InBodyModelProfile(
        model_id="770S",
        name="InBody 770S",
        tier="professional",
        install_type="separable",
        tone_profile="professional",
        measurement_items=(
            "체수분량", "단백질량", "무기질량", "체지방량", "체중",
            "골격근량", "BMI", "체지방률", "내장지방면적",
            "세포외수분비(ECW/TBW)", "부위별 근육량", "부위별 체지방량",
        ),
        description="병원 및 대학 연구실용 전문가형 체성분 분석기",
    ),
    "970S": InBodyModelProfile(
        model_id="970S",
        name="InBody 970S",
        tier="professional",
        install_type="separable",
        tone_profile="professional",
        measurement_items=(
            "체수분량", "단백질량", "무기질량", "체지방량", "체중",
            "골격근량", "BMI", "체지방률", "내장지방면적",
            "세포외수분비(ECW/TBW)", "부위별 근육량", "부위별 체지방량",
            "부위별 체수분량", "부위별 세포외수분비", "위상각(Phase Angle)",
        ),
        description="종합병원 및 대규모 연구기관용 최상위 전문가형 체성분 분석기",
    ),
}


def get_model_profile(model_id: str) -> InBodyModelProfile | None:
    """기종 ID로 프로필 조회 — 미지원 기종이면 None 반환"""
    return INBODY_MODELS.get(model_id)


def is_supported_model(model_id: str) -> bool:
    """지원 기종 여부 확인"""
    return model_id in SUPPORTED_MODELS
