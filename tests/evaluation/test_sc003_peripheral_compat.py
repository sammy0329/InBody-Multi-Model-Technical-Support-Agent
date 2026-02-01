"""SC-003 평가: 주변기기 호환 정보 키워드 검증

check_peripheral_compatibility 도구가 반환하는 응답에
매뉴얼 기반 필수 키워드(호환 상태, 연결 방식, 설정 절차)가
포함되는지 검증한다.
"""

from unittest.mock import patch

import pytest

from src.tools.peripheral_tool import check_peripheral_compatibility

# ── 주변기기별 필수 키워드 — peripheral_compatibility.json 기반 ──
# (model, type, name): {"compatible": bool, "connection": 연결 방식, "keywords": 설정 절차 키워드}
PERIPHERAL_KEYWORD_MAP = {
    # ── 270S (7개) ──
    ("270S", "printer", "삼성 SL-M2035"): {
        "compatible": True,
        "connection": "USB",
        "keywords": ["프린터 케이블", "USB 포트", "시범인쇄"],
    },
    ("270S", "printer", "렉스마크 MS312DN"): {
        "compatible": True,
        "connection": "USB",
        "keywords": ["프린터 케이블", "관리자 메뉴", "시범인쇄"],
    },
    ("270S", "printer", "삼성 SL-M2027W"): {
        "compatible": True,
        "connection": "USB / Wi-Fi",
        "keywords": ["Wi-Fi", "시범인쇄"],
    },
    ("270S", "printer", "삼성 SL-C563FW"): {
        "compatible": True,
        "connection": "USB",
        "keywords": ["프린터 케이블", "시범인쇄"],
    },
    ("270S", "printer", "HP 레이저젯 프로 M203DW"): {
        "compatible": True,
        "connection": "USB",
        "keywords": ["프린터 케이블", "시범인쇄"],
    },
    ("270S", "pc", "Lookin'Body 120"): {
        "compatible": True,
        "connection": "USB",
        "keywords": ["소프트웨어", "USB 케이블", "데이터 동기화"],
    },
    ("270S", "barcode_reader", "USB 바코드 리더기"): {
        "compatible": True,
        "connection": "USB HID",
        "keywords": ["USB 포트", "HID"],
    },
    # ── 580 (4개) ──
    ("580", "printer", "PCL3"): {
        "compatible": True,
        "connection": "USB / Wi-Fi",
        "keywords": ["프린터 찾기", "시범인쇄"],
    },
    ("580", "pc", "Lookin'Body 120"): {
        "compatible": True,
        "connection": "USB / LAN",
        "keywords": ["소프트웨어", "네트워크"],
    },
    ("580", "barcode_reader", "USB 바코드 리더기"): {
        "compatible": True,
        "connection": "USB HID",
        "keywords": ["USB 포트"],
    },
    ("580", "usb", "USB 메모리"): {
        "compatible": True,
        "connection": "USB",
        "keywords": ["FAT32", "데이터 관리"],
    },
    # ── 770S (7개) ──
    ("770S", "printer", "삼성 SL-M2035"): {
        "compatible": True,
        "connection": "USB",
        "keywords": ["프린터 케이블", "시범인쇄"],
    },
    ("770S", "printer", "렉스마크 MS312DN"): {
        "compatible": True,
        "connection": "USB",
        "keywords": ["프린터 케이블", "관리자 메뉴"],
    },
    ("770S", "printer", "삼성 SL-M2027W"): {
        "compatible": True,
        "connection": "USB / Wi-Fi",
        "keywords": ["Wi-Fi", "시범인쇄"],
    },
    ("770S", "printer", "HP 레이저젯 프로 M203DW"): {
        "compatible": True,
        "connection": "USB",
        "keywords": ["프린터 케이블", "시범인쇄"],
    },
    ("770S", "pc", "Lookin'Body 120"): {
        "compatible": True,
        "connection": "USB / LAN / RS-232C",
        "keywords": ["소프트웨어", "RS-232C", "통신 포트"],
    },
    ("770S", "barcode_reader", "USB 바코드 리더기"): {
        "compatible": True,
        "connection": "USB HID",
        "keywords": ["USB 포트", "HID"],
    },
    ("770S", "pc", "병원 EMR/HIS"): {
        "compatible": True,
        "connection": "LAN (HL7/DICOM)",
        "keywords": ["HL7", "EMR"],
    },
    # ── 970S (7개) ──
    ("970S", "printer", "삼성 SL-M2035"): {
        "compatible": True,
        "connection": "USB",
        "keywords": ["프린터 케이블", "시범인쇄"],
    },
    ("970S", "printer", "렉스마크 MS312DN"): {
        "compatible": True,
        "connection": "USB",
        "keywords": ["프린터 케이블", "관리자 메뉴"],
    },
    ("970S", "printer", "삼성 SL-M2027W"): {
        "compatible": True,
        "connection": "USB / Wi-Fi",
        "keywords": ["Wi-Fi", "시범인쇄"],
    },
    ("970S", "printer", "HP 레이저젯 프로 M203DW"): {
        "compatible": True,
        "connection": "USB",
        "keywords": ["프린터 케이블", "시범인쇄"],
    },
    ("970S", "pc", "Lookin'Body 120"): {
        "compatible": True,
        "connection": "USB / LAN / RS-232C",
        "keywords": ["소프트웨어", "Export"],
    },
    ("970S", "barcode_reader", "USB 바코드 리더기"): {
        "compatible": True,
        "connection": "USB HID",
        "keywords": ["USB 포트", "HID"],
    },
    ("970S", "pc", "병원 EMR/HIS"): {
        "compatible": True,
        "connection": "LAN (HL7/DICOM)",
        "keywords": ["HL7", "DICOM"],
    },
}

PERIPHERAL_CASES = list(PERIPHERAL_KEYWORD_MAP.items())


@pytest.mark.evaluation
@pytest.mark.sc003
@pytest.mark.parametrize(
    "periph_key, expected",
    PERIPHERAL_CASES,
    ids=[f"sc003_{m}_{t}_{n[:8]}" for (m, t, n), _ in PERIPHERAL_CASES],
)
async def test_sc003_peripheral_compat_keywords(
    periph_key, expected, seeded_session_factory, sc_metrics
):
    """SC-003: 주변기기 호환 조회 응답에 호환 상태, 연결 방식, 설정 키워드가 포함된다."""
    model, ptype, pname = periph_key

    with patch(
        "src.tools.peripheral_tool.async_session_factory",
        seeded_session_factory,
    ):
        result = await check_peripheral_compatibility.ainvoke(
            {"model": model, "peripheral_type": ptype, "peripheral_name": pname}
        )

    # 1) 호환 상태 확인
    if expected["compatible"]:
        compat_ok = "호환" in result and "호환 정보가 없습니다" not in result
    else:
        compat_ok = "비호환" in result

    # 2) 연결 방식 키워드 포함
    connection_ok = expected["connection"] in result

    # 3) 설정 절차 필수 키워드 포함
    missing_keywords = [kw for kw in expected["keywords"] if kw not in result]
    keywords_ok = len(missing_keywords) == 0

    passed = compat_ok and connection_ok and keywords_ok
    sc_metrics.record("SC-003", passed)

    assert passed, (
        f"{model}/{ptype}/{pname}: "
        f"compat_ok={compat_ok}, connection_ok={connection_ok}, "
        f"missing_keywords={missing_keywords}"
    )
