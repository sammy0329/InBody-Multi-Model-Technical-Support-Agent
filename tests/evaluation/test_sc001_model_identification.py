"""SC-001 평가: 텍스트 기반 기종 식별 정확도 ≥ 95%

40개 한국어 입력에 대해 _pre_extract_model()의 정확도를 측정한다.
LLM 호출 없이 정규식 경로만 평가하므로 API 키 불필요.
"""

import pytest

from src.graph.nodes.model_router import _pre_extract_model

SC001_CASES = [
    # 직접 언급 (16 cases: 4 models x 4 patterns)
    ("InBody 270S 설치 방법 알려주세요", "270S"),
    ("270S 에러 코드 E001", "270S"),
    ("인바디 270s 사용법", "270S"),
    ("270S와 관련된 질문입니다", "270S"),
    ("InBody 580 측정 결과 해석", "580"),
    ("580 프린터 연결 안 돼요", "580"),
    ("인바디 580에서 에러 발생", "580"),
    ("580을 사용 중인데요", "580"),
    ("InBody 770S 캘리브레이션", "770S"),
    ("770S ECW/TBW 비율", "770S"),
    ("인바디 770s 설치", "770S"),
    ("770S에서 데이터 전송 오류", "770S"),
    ("InBody 970S 위상각 해석", "970S"),
    ("970S QC 실패", "970S"),
    ("인바디 970s 연구 데이터 내보내기", "970S"),
    ("970S에 대해 알려주세요", "970S"),
    # 비공식적 표현 (8 cases)
    ("270s 좀 알려주세요", "270S"),
    ("580에서 화면이 안 켜져요", "580"),
    ("770s 부위별 근육량", "770S"),
    ("970s 다주파수 임피던스", "970S"),
    ("제가 쓰는 건 270S인데요", "270S"),
    ("우리 병원 580", "580"),
    ("770S 모델 사용자입니다", "770S"),
    ("970S 장비 관련 문의", "970S"),
    # 문맥 속 기종명 (8 cases)
    ("체육관에서 270S 사용하고 있는데 에러가 납니다", "270S"),
    ("학교 체력 측정실에 580이 설치되어 있어요", "580"),
    ("연구실에서 770S로 실험 중입니다", "770S"),
    ("병원에서 970S 결과지가 인쇄 안 돼요", "970S"),
    ("270S 처음 설치하는 건데요", "270S"),
    ("580 전극 청소 방법이요", "580"),
    ("770S Lookin'Body 연동", "770S"),
    ("970S 네트워크 설정", "970S"),
    # 한국어 조사 결합 (8 cases)
    ("270S의 장단점", "270S"),
    ("580은 어떤 기종인가요", "580"),
    ("770S가 좋은 이유", "770S"),
    ("970S를 구매했는데", "970S"),
    ("270S에서는 체수분량 측정이 되나요", "270S"),
    ("580도 부위별 측정이 가능한가요", "580"),
    ("770S만 가지고 있어요", "770S"),
    ("970S부터는 위상각이 있나요", "970S"),
]


@pytest.mark.evaluation
@pytest.mark.sc001
@pytest.mark.parametrize(
    "message, expected_model",
    SC001_CASES,
    ids=[f"sc001_{i:02d}" for i in range(len(SC001_CASES))],
)
def test_sc001_model_identification(message, expected_model, sc_metrics):
    """SC-001: 텍스트 입력에서 기종을 정확히 식별한다."""
    result = _pre_extract_model(message)
    passed = result == expected_model
    sc_metrics.record("SC-001", passed)
    assert passed, f"입력: {message!r}, 기대: {expected_model}, 실제: {result}"
