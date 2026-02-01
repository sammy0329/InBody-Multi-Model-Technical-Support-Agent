"""섹션 맵 기반 인접 섹션 조회 유틸리티

매뉴얼의 목차 구조를 활용하여, 현재 질문에 해당하는 섹션을 식별하고
같은 챕터의 형제 섹션(다음/이전)을 반환한다.
에이전트가 후속 질문을 매뉴얼 구조에 기반하여 제안할 수 있도록 돕는다.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

SECTION_MAPS_DIR = Path(__file__).parent.parent.parent / "data" / "section_maps"


@lru_cache(maxsize=4)
def _load_section_map(model: str) -> dict | None:
    """기종별 섹션 맵 JSON을 로드한다 (캐시)."""
    path = SECTION_MAPS_DIR / f"{model}.json"
    if not path.exists():
        logger.warning("섹션 맵 파일 없음: %s", path)
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _flatten_sections(section_map: dict) -> list[dict]:
    """챕터 구조를 평탄화하여 (chapter_id, section) 쌍의 리스트로 반환."""
    flat = []
    for chapter in section_map.get("chapters", []):
        chapter_id = chapter["id"]
        chapter_title = chapter["title"]
        for section in chapter.get("sections", []):
            flat.append({
                "chapter_id": chapter_id,
                "chapter_title": chapter_title,
                **section,
            })
    return flat


def _score_section(section: dict, query: str) -> int:
    """질문과 섹션 키워드의 매칭 점수를 계산한다."""
    query_lower = query.lower()
    score = 0
    for keyword in section.get("keywords", []):
        if keyword.lower() in query_lower:
            score += len(keyword)
    if section["title"].lower() in query_lower:
        score += len(section["title"]) * 2
    return score


def get_adjacent_sections(model: str, query: str) -> str:
    """현재 질문에 매칭되는 섹션을 찾고, 같은 챕터의 인접 섹션 정보를 반환한다.

    Args:
        model: InBody 기종
        query: 사용자 질문

    Returns:
        인접 섹션 정보 문자열. 매칭 실패 시 빈 문자열.
    """
    section_map = _load_section_map(model)
    if not section_map:
        return ""

    flat = _flatten_sections(section_map)
    if not flat:
        return ""

    # 질문과 가장 잘 매칭되는 섹션 찾기
    scored = [(s, _score_section(s, query)) for s in flat]
    scored.sort(key=lambda x: x[1], reverse=True)
    best, best_score = scored[0]

    if best_score == 0:
        return ""

    # 같은 챕터의 형제 섹션 추출
    chapter_id = best["chapter_id"]
    siblings = [s for s in flat if s["chapter_id"] == chapter_id]

    current_idx = next(
        (i for i, s in enumerate(siblings) if s["id"] == best["id"]),
        -1,
    )
    if current_idx == -1:
        return ""

    lines = [f"현재 섹션: {best['title']}"]
    lines.append(f"상위 챕터: {best['chapter_title']}")

    # 이전 섹션
    if current_idx > 0:
        prev_sec = siblings[current_idx - 1]
        lines.append(f"이전 섹션: {prev_sec['title']}")

    # 다음 섹션
    if current_idx < len(siblings) - 1:
        next_sec = siblings[current_idx + 1]
        lines.append(f"다음 섹션: {next_sec['title']}")

    # 같은 챕터 전체 목차
    toc = " → ".join(s["title"] for s in siblings)
    lines.append(f"챕터 목차: {toc}")

    return "\n".join(lines)
