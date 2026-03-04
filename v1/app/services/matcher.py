"""키워드 매칭 엔진.

사용자의 자유 입력 텍스트에서 형태소를 추출하고,
Playbook 키워드와 매칭하여 가장 적합한 민원 유형을 찾는다.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.playbook import Playbook
from app.services.playbook import get_all_playbooks, get_keyword_index

_kiwi = None
_TARGET_POS = {"NNG", "NNP", "NNB", "VV", "VA", "SL"}


def _get_kiwi():
    """Kiwi 인스턴스를 최초 호출 시 한 번만 생성한다."""
    global _kiwi
    if _kiwi is None:
        from kiwipiepy import Kiwi
        _kiwi = Kiwi()
    return _kiwi


@dataclass
class MatchResult:
    playbook: Playbook
    score: float
    matched_keywords: list[str]


def extract_keywords(text: str) -> list[str]:
    """사용자 입력에서 의미 있는 키워드를 추출한다.

    1글자 명사도 포함 — "세금"이 "세"+"금"으로 분리되는 경우 대응.
    단, 조사/어미 등 기능어는 제외 (품사 필터).
    """
    kiwi = _get_kiwi()
    tokens = kiwi.tokenize(text)
    return [token.form for token in tokens if token.tag in _TARGET_POS]


def match_playbook(text: str) -> MatchResult | None:
    """사용자 입력과 가장 잘 맞는 Playbook을 반환한다.

    1단계: 형태소 추출 후 키워드 인덱스에서 정확 매칭
    2단계: 원문에서 부분 문자열 매칭 (폴백)
    """
    user_keywords = extract_keywords(text)
    keyword_index = get_keyword_index()
    all_playbooks = get_all_playbooks()

    if not all_playbooks:
        return None

    scores: dict[str, tuple[float, list[str]]] = {}

    for uk in user_keywords:
        if uk in keyword_index:
            for pb_id in keyword_index[uk]:
                if pb_id not in scores:
                    scores[pb_id] = (0.0, [])
                current_score, matched = scores[pb_id]
                matched.append(uk)
                scores[pb_id] = (current_score + 1.0, matched)

    if not scores:
        for pb in all_playbooks.values():
            matched = [kw for kw in pb.keywords if kw in text]
            if matched:
                scores[pb.id] = (len(matched) * 0.5, matched)

    if not scores:
        return None

    best_id = max(scores, key=lambda k: scores[k][0])
    best_score, best_matched = scores[best_id]
    pb = all_playbooks[best_id]
    max_possible = len(pb.keywords)
    normalized_score = min(best_score / max(max_possible, 1), 1.0)

    return MatchResult(
        playbook=pb,
        score=normalized_score,
        matched_keywords=best_matched,
    )
