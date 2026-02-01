"""연동 에이전트 유틸리티 단위 테스트

주변기기 유형/이름 추출 로직을 검증한다.
"""

import pytest

from src.graph.nodes.connect_agent import _extract_peripheral_name, _extract_peripheral_type


# ── _extract_peripheral_type ──


@pytest.mark.unit
@pytest.mark.parametrize(
    "message, expected",
    [
        ("프린터 연결 방법 알려주세요", "printer"),
        ("결과지 인쇄가 안 돼요", "printer"),
        ("출력 설정 확인", "printer"),
        ("PC 연동 방법", "pc"),
        ("컴퓨터에 데이터 전송", "pc"),
        ("룩인바디 소프트웨어 설치", "pc"),
        ("LookInBody 연결", "pc"),
        ("Lookin'Body 설정", "pc"),
        ("EMR 시스템 연동", "pc"),
        ("LAN 네트워크 연결", "pc"),
        ("바코드 리더기 설정", "barcode_reader"),
        ("스캐너 연결", "barcode_reader"),
        ("USB 메모리 사용", "usb"),
    ],
)
def test_extract_peripheral_type(message, expected):
    """주변기기 유형 키워드를 정확히 분류한다."""
    assert _extract_peripheral_type(message) == expected


@pytest.mark.unit
def test_extract_peripheral_type_no_match():
    """주변기기 키워드가 없으면 빈 문자열을 반환한다."""
    assert _extract_peripheral_type("270S 설치 방법") == ""


# ── _extract_peripheral_name ──


@pytest.mark.unit
@pytest.mark.parametrize(
    "message, expected",
    [
        ("Lookin'Body 연동 방법을 알려주세요", "Lookin'Body"),
        ("LookInBody 소프트웨어 설치", "LookInBody"),
        ("룩인바디 프로그램 연결", "룩인바디"),
        ("EMR 시스템과 연동하고 싶습니다", "EMR"),
        ("HIS 연동 가능한가요", "HIS"),
        ("DICOM 프로토콜 지원 여부", "DICOM"),
        ("HL7 인터페이스 설정", "HL7"),
    ],
)
def test_extract_peripheral_name(message, expected):
    """주변기기 이름 키워드를 정확히 추출한다."""
    assert _extract_peripheral_name(message) == expected


@pytest.mark.unit
def test_extract_peripheral_name_no_match():
    """주변기기 이름 키워드가 없으면 빈 문자열을 반환한다."""
    assert _extract_peripheral_name("프린터 연결 안 돼요") == ""
