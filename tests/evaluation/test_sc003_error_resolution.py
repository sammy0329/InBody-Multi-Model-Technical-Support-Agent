"""SC-003 평가: 에러 코드 해결 정보 키워드 검증

lookup_error_code 도구가 반환하는 응답에 매뉴얼 기반 필수 키워드가
포함되는지 검증한다. LLM 호출 없이 데이터 소스 → 도구 → 응답의
end-to-end 정확성을 측정한다.
"""

from unittest.mock import patch

import pytest

from src.tools.error_code_tool import lookup_error_code

# ── 에러코드별 필수 키워드 — error_codes.json 및 매뉴얼 기반 ──
# (model, code): {"title": 제목 키워드, "level": 지원 수준 텍스트, "keywords": 해결 단계 필수 키워드}
ERROR_KEYWORD_MAP = {
    # ── 270S ──
    ("270S", "E001"): {
        "title": "전극 접촉 불량",
        "level": "사용자 해결 가능 (Level 1)",
        "keywords": ["전극", "전해질 티슈", "재측정"],
    },
    ("270S", "E002"): {
        "title": "체중 센서 오류",
        "level": "사용자 해결 가능 (Level 1)",
        "keywords": ["캘리브레이션", "평평한 바닥", "재시작"],
    },
    ("270S", "E003"): {
        "title": "프린터 통신 오류",
        "level": "사용자 해결 가능 (Level 1)",
        "keywords": ["USB 케이블", "프린터 전원", "USB 포트"],
    },
    ("270S", "E010"): {
        "title": "디스플레이 표시 오류",
        "level": "서비스 센터 이관 필요 (Level 3)",
        "keywords": ["재시작", "서비스 센터"],
    },
    ("270S", "E020"): {
        "title": "메인보드 통신 오류",
        "level": "서비스 센터 이관 필요 (Level 3)",
        "keywords": ["전원 케이블", "서비스 센터"],
    },
    # ── 580 ──
    ("580", "E001"): {
        "title": "전극 접촉 불량",
        "level": "사용자 해결 가능 (Level 1)",
        "keywords": ["전극", "전해질 티슈", "재측정"],
    },
    ("580", "E004"): {
        "title": "네트워크 연결 실패",
        "level": "사용자 해결 가능 (Level 1)",
        "keywords": ["LAN 케이블", "IP 주소"],
    },
    ("580", "E005"): {
        "title": "소프트웨어 업데이트 실패",
        "level": "사용자 해결 가능 (Level 1)",
        "keywords": ["USB 메모리", "FAT32"],
    },
    ("580", "E011"): {
        "title": "체중 센서 이상",
        "level": "서비스 센터 이관 필요 (Level 3)",
        "keywords": ["캘리브레이션", "서비스 센터"],
    },
    ("580", "E021"): {
        "title": "터치스크린 무반응",
        "level": "서비스 센터 이관 필요 (Level 3)",
        "keywords": ["재시작", "서비스 센터"],
    },
    # ── 770S ──
    ("770S", "E001"): {
        "title": "전극 임피던스 측정 오류",
        "level": "사용자 해결 가능 (Level 1)",
        "keywords": ["전극", "알코올 패드", "케이블 커넥터"],
    },
    ("770S", "E006"): {
        "title": "데이터 전송 프로토콜 오류",
        "level": "사용자 해결 가능 (Level 1)",
        "keywords": ["Lookin'Body", "COM 포트", "드라이버"],
    },
    ("770S", "E012"): {
        "title": "ECW/TBW 비율 센서 이상",
        "level": "서비스 센터 이관 필요 (Level 3)",
        "keywords": ["자가 진단", "서비스 센터"],
    },
    ("770S", "E022"): {
        "title": "부위별 측정 편차 과대",
        "level": "서비스 센터 이관 필요 (Level 3)",
        "keywords": ["전극 접촉", "서비스 센터"],
    },
    ("770S", "E030"): {
        "title": "자동 캘리브레이션 실패",
        "level": "사용자 해결 가능 (Level 1)",
        "keywords": ["온도", "수동 캘리브레이션"],
    },
    # ── 970S ──
    ("970S", "E001"): {
        "title": "다주파수 임피던스 측정 오류",
        "level": "사용자 해결 가능 (Level 1)",
        "keywords": ["전극", "전자기 간섭"],
    },
    ("970S", "E007"): {
        "title": "위상각",
        "level": "서비스 센터 이관 필요 (Level 3)",
        "keywords": ["자가 진단", "서비스 센터"],
    },
    ("970S", "E008"): {
        "title": "부위별 체수분 분포 편차",
        "level": "서비스 센터 이관 필요 (Level 3)",
        "keywords": ["전극 접촉", "교차 검증", "서비스 센터"],
    },
    ("970S", "E013"): {
        "title": "연구 데이터 내보내기 오류",
        "level": "사용자 해결 가능 (Level 1)",
        "keywords": ["USB 저장 장치", "FAT32"],
    },
    ("970S", "E031"): {
        "title": "자동 QC",
        "level": "사용자 해결 가능 (Level 1)",
        "keywords": ["온도", "습도"],
    },
}

ERROR_CASES = list(ERROR_KEYWORD_MAP.items())


@pytest.mark.evaluation
@pytest.mark.sc003
@pytest.mark.parametrize(
    "error_key, expected",
    ERROR_CASES,
    ids=[f"sc003_{m}_{c}" for (m, c), _ in ERROR_CASES],
)
async def test_sc003_error_resolution_keywords(
    error_key, expected, seeded_session_factory, sc_metrics
):
    """SC-003: 에러 코드 조회 응답에 제목, 지원 수준, 해결 키워드가 포함된다."""
    model, code = error_key

    with patch(
        "src.tools.error_code_tool.async_session_factory",
        seeded_session_factory,
    ):
        result = await lookup_error_code.ainvoke(
            {"model": model, "error_code": code}
        )

    # 1) 제목 키워드 포함
    title_ok = expected["title"] in result

    # 2) 지원 수준 텍스트 일치
    level_ok = expected["level"] in result

    # 3) 해결 단계 필수 키워드 포함
    missing_keywords = [kw for kw in expected["keywords"] if kw not in result]
    keywords_ok = len(missing_keywords) == 0

    passed = title_ok and level_ok and keywords_ok
    sc_metrics.record("SC-003", passed)

    assert passed, (
        f"{model}/{code}: "
        f"title_ok={title_ok}, level_ok={level_ok}, "
        f"missing_keywords={missing_keywords}"
    )
