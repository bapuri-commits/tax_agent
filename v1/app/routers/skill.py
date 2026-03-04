"""카카오 오픈빌더 스킬 엔드포인트.

대화 흐름:
  1. "처음으로" / 첫 진입 → 인사 + 카테고리 메뉴
  2. 카테고리명 입력 → 해당 카테고리 민원 목록
  3. 민원 유형명 입력 → 조건 분기 질문
  4. 조건 값 입력 → 최종 응답 (다중 조건 시 답변을 축적)
  5. 자유 입력 → 키워드 매칭 → 성공 시 조건 질문, 실패 시 폴백
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter

from app.models.kakao import KakaoSkillRequest, KakaoSkillResponse
from app.services import formatter, playbook
from app.services.matcher import match_playbook

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/skill", tags=["skill"])

SESSION_TTL_SECONDS = 600  # 10분 무응답 시 세션 만료
SESSION_CLEANUP_THRESHOLD = 1000  # 세션이 이 수를 넘으면 정리 수행

_sessions: dict[str, dict] = {}


def _get_session(user_id: str) -> dict:
    now = time.time()
    if user_id in _sessions:
        session = _sessions[user_id]
        session["last_active"] = now
        return session

    session = {
        "state": "idle",
        "playbook_id": None,
        "condition_idx": 0,
        "answers": {},  # param_name → answer_value
        "last_active": now,
    }
    _sessions[user_id] = session
    return session


def _reset_session(user_id: str) -> None:
    _sessions.pop(user_id, None)


def _cleanup_expired_sessions() -> None:
    """만료된 세션을 정리한다. 요청 처리 중 주기적으로 호출."""
    if len(_sessions) < SESSION_CLEANUP_THRESHOLD:
        return
    now = time.time()
    expired = [
        uid for uid, s in _sessions.items()
        if now - s["last_active"] > SESSION_TTL_SECONDS
    ]
    for uid in expired:
        del _sessions[uid]
    if expired:
        logger.info("세션 정리: %d개 만료 세션 제거, 잔여 %d개", len(expired), len(_sessions))


@router.post("/message", response_model=KakaoSkillResponse, response_model_exclude_none=True)
async def handle_message(req: KakaoSkillRequest) -> KakaoSkillResponse:
    user_id = req.userRequest.user.id
    utterance = req.userRequest.utterance.strip()

    logger.info("요청 수신 | user=%s | utterance='%s'", user_id[:8], utterance)

    _cleanup_expired_sessions()
    session = _get_session(user_id)

    if utterance in ("처음으로", "시작", "다른 질문하기"):
        _reset_session(user_id)
        response = formatter.build_greeting()
        logger.info("응답: 인사 메시지")
        return response

    state = session["state"]

    if state == "idle":
        return _handle_idle(user_id, utterance, session)

    if state == "waiting_condition":
        return _handle_condition_answer(user_id, utterance, session)

    _reset_session(user_id)
    return formatter.build_greeting()


def _handle_idle(user_id: str, utterance: str, session: dict) -> KakaoSkillResponse:
    categories = playbook.get_categories()
    if utterance in categories:
        logger.info("카테고리 매칭: %s", utterance)
        return formatter.build_category_menu(utterance, categories[utterance])

    for pb in playbook.get_all_playbooks().values():
        if pb.name == utterance:
            logger.info("민원 유형 정확 매칭: %s", pb.id)
            return _start_playbook(user_id, pb.id, session)

    result = match_playbook(utterance)
    if result and result.score >= 0.1:
        logger.info(
            "키워드 매칭: %s (score=%.2f, keywords=%s)",
            result.playbook.id, result.score, result.matched_keywords,
        )
        return _start_playbook(user_id, result.playbook.id, session)

    logger.info("매칭 실패 → 폴백")
    return formatter.build_fallback()


def _start_playbook(user_id: str, playbook_id: str, session: dict) -> KakaoSkillResponse:
    pb = playbook.get_playbook(playbook_id)
    if pb is None:
        return formatter.build_fallback()

    if pb.conditions:
        session["state"] = "waiting_condition"
        session["playbook_id"] = playbook_id
        session["condition_idx"] = 0
        session["answers"] = {}
        return formatter.build_condition_question(pb, pb.conditions[0])

    first_key = next(iter(pb.responses))
    return formatter.build_final_response(pb, pb.responses[first_key])


def _build_response_key(answers: dict[str, str]) -> str:
    """축적된 답변들로 응답 키를 생성한다.

    답변이 1개면 그 값 자체가 키 (예: "self"),
    여러 개면 언더스코어로 연결 (예: "self_yes").
    """
    values = list(answers.values())
    return "_".join(values)


def _handle_condition_answer(
    user_id: str, utterance: str, session: dict
) -> KakaoSkillResponse:
    pb = playbook.get_playbook(session["playbook_id"])
    if pb is None:
        _reset_session(user_id)
        return formatter.build_fallback()

    condition_idx = session["condition_idx"]
    if condition_idx >= len(pb.conditions):
        _reset_session(user_id)
        return formatter.build_fallback()

    condition = pb.conditions[condition_idx]

    valid_values = {opt.value for opt in condition.options}
    label_to_value = {opt.label: opt.value for opt in condition.options}

    answer = utterance
    if answer in label_to_value:
        answer = label_to_value[answer]

    if answer not in valid_values:
        logger.info("유효하지 않은 답변 '%s' → 질문 재시도", utterance)
        return formatter.build_condition_question(pb, condition)

    session["answers"][condition.param] = answer

    next_idx = condition_idx + 1
    if next_idx < len(pb.conditions):
        session["condition_idx"] = next_idx
        return formatter.build_condition_question(pb, pb.conditions[next_idx])

    # 모든 조건 수집 완료 → 응답 키 결정
    response_key = _build_response_key(session["answers"])
    _reset_session(user_id)

    if response_key in pb.responses:
        logger.info("최종 응답: playbook=%s, key=%s", pb.id, response_key)
        return formatter.build_final_response(pb, pb.responses[response_key])

    # 복합 키로 못 찾으면 마지막 답변 단독으로 시도
    if answer in pb.responses:
        logger.info("최종 응답 (단일 키 폴백): playbook=%s, key=%s", pb.id, answer)
        return formatter.build_final_response(pb, pb.responses[answer])

    first_key = next(iter(pb.responses))
    logger.warning("응답 키 '%s' 미발견 → 첫 번째 응답 폴백", response_key)
    return formatter.build_final_response(pb, pb.responses[first_key])
