"""카카오 오픈빌더 스킬 요청/응답 Pydantic 모델.

공식 문서: https://i.kakao.com/docs/skill-response-format
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


# ──────────────────────────────────────────────
# 요청 (카카오 → 스킬 서버)
# ──────────────────────────────────────────────


class Bot(BaseModel):
    id: str
    name: str | None = None


class User(BaseModel):
    id: str
    type: str | None = None
    properties: dict[str, Any] | None = None


class UserRequest(BaseModel):
    timezone: str | None = None
    block: dict[str, Any] | None = None
    utterance: str
    lang: str | None = None
    user: User


class Action(BaseModel):
    id: str | None = None
    name: str | None = None
    params: dict[str, str] = {}
    detailParams: dict[str, Any] = {}
    clientExtra: dict[str, Any] | None = None


class KakaoSkillRequest(BaseModel):
    """카카오 오픈빌더가 스킬 서버로 보내는 요청 전체."""

    bot: Bot | None = None
    intent: dict[str, Any] | None = None
    action: Action | None = None
    userRequest: UserRequest
    contexts: list[dict[str, Any]] | None = None


# ──────────────────────────────────────────────
# 응답 (스킬 서버 → 카카오)
# ──────────────────────────────────────────────


class Button(BaseModel):
    label: str
    action: str  # "webLink" | "message" | "phone" | "block"
    webLinkUrl: str | None = None
    messageText: str | None = None
    phoneNumber: str | None = None
    blockId: str | None = None


class SimpleText(BaseModel):
    text: str


class TextCard(BaseModel):
    title: str
    description: str
    buttons: list[Button] = []


class SimpleTextOutput(BaseModel):
    simpleText: SimpleText


class TextCardOutput(BaseModel):
    textCard: TextCard


class QuickReply(BaseModel):
    label: str
    action: str = "message"
    messageText: str


class SkillTemplate(BaseModel):
    outputs: list[SimpleTextOutput | TextCardOutput]
    quickReplies: list[QuickReply] | None = None


class KakaoSkillResponse(BaseModel):
    """카카오 오픈빌더에 반환하는 응답."""

    version: str = "2.0"
    template: SkillTemplate
