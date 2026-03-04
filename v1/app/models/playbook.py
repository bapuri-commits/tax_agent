"""Playbook 데이터 모델.

각 민원 유형을 하나의 Playbook JSON으로 표현한다.
조건 분기(conditions) → 최종 응답(responses) 구조.
"""

from __future__ import annotations

from pydantic import BaseModel


class ConditionOption(BaseModel):
    label: str
    value: str


class Condition(BaseModel):
    """사용자에게 물어볼 조건 분기 질문."""

    question: str
    param: str
    options: list[ConditionOption]


class Method(BaseModel):
    name: str
    url: str | None = None
    address: str | None = None


class Link(BaseModel):
    title: str
    url: str


class Department(BaseModel):
    name: str
    phone: str


class PlaybookResponse(BaseModel):
    """조건 조합에 따른 최종 응답 데이터."""

    conclusion: str
    documents: list[str] = []
    methods: dict[str, Method] = {}
    links: list[Link] = []
    department: Department


class Playbook(BaseModel):
    """하나의 민원 유형을 표현하는 Playbook."""

    id: str
    name: str
    category: str
    keywords: list[str]
    conditions: list[Condition] = []
    responses: dict[str, PlaybookResponse]
