"""톤앤매너 프로파일 단위 테스트

기종별 톤 매핑과 톤 지시문 반환 로직을 검증한다.
"""

import pytest

from src.models.inbody_models import SUPPORTED_MODELS, get_model_profile
from src.prompts.tone_profiles import TONE_PROFILES, get_tone_instruction


@pytest.mark.unit
def test_casual_tone_contains_friendly():
    """casual 톤 지시문에 '친근' 키워드가 포함된다."""
    instruction = get_tone_instruction("casual")
    assert isinstance(instruction, str)
    assert len(instruction) > 0
    assert "친근" in instruction


@pytest.mark.unit
def test_professional_tone_contains_expert():
    """professional 톤 지시문에 '전문' 키워드가 포함된다."""
    instruction = get_tone_instruction("professional")
    assert isinstance(instruction, str)
    assert len(instruction) > 0
    assert "전문" in instruction


@pytest.mark.unit
def test_invalid_tone_raises_value_error():
    """존재하지 않는 톤 프로파일은 ValueError를 발생시킨다."""
    with pytest.raises(ValueError, match="지원하지 않는 톤 프로파일"):
        get_tone_instruction("unknown")


@pytest.mark.unit
@pytest.mark.parametrize(
    "model_id, expected_tone, expected_tier",
    [
        ("270S", "casual", "entry"),
        ("580", "casual", "entry"),
        ("770S", "professional", "professional"),
        ("970S", "professional", "professional"),
    ],
)
def test_model_tone_and_tier_mapping(model_id, expected_tone, expected_tier):
    """각 기종이 올바른 톤 프로파일과 티어에 매핑된다."""
    profile = get_model_profile(model_id)
    assert profile.tone_profile == expected_tone
    assert profile.tier == expected_tier


@pytest.mark.unit
def test_all_models_have_complete_profiles():
    """모든 지원 기종이 필수 프로필 필드를 가진다."""
    for model_id in SUPPORTED_MODELS:
        profile = get_model_profile(model_id)
        assert profile is not None
        assert len(profile.measurement_items) > 0
        assert len(profile.description) > 0
        assert profile.install_type in ("foldable", "separable")
        assert profile.tone_profile in TONE_PROFILES
