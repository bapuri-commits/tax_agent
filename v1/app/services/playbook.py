"""Playbook 로딩 및 조회 서비스.

서버 시작 시 JSON 파일들을 메모리에 올려두고 사용한다.
민원 유형이 30개 수준이라 메모리 부담 없음.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.config import PLAYBOOK_DIR
from app.models.playbook import Playbook

logger = logging.getLogger(__name__)

_playbooks: dict[str, Playbook] = {}
_keyword_index: dict[str, list[str]] = {}


def load_playbooks(directory: Path = PLAYBOOK_DIR) -> None:
    """playbooks 디렉토리의 JSON 파일을 전부 로드한다.

    개별 파일 오류 시 해당 파일만 건너뛰고 계속 진행한다.
    """
    _playbooks.clear()
    _keyword_index.clear()

    for path in sorted(directory.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            pb = Playbook(**data)
            _playbooks[pb.id] = pb
            for kw in pb.keywords:
                _keyword_index.setdefault(kw, []).append(pb.id)
            logger.info("Playbook 로드 성공: %s (%s)", pb.id, pb.name)
        except Exception:
            logger.exception("Playbook 로드 실패: %s", path.name)

    logger.info("총 %d개 Playbook 로드 완료", len(_playbooks))


def get_playbook(playbook_id: str) -> Playbook | None:
    return _playbooks.get(playbook_id)


def get_all_playbooks() -> dict[str, Playbook]:
    return _playbooks


def get_keyword_index() -> dict[str, list[str]]:
    return _keyword_index


def get_categories() -> dict[str, list[Playbook]]:
    """카테고리별로 Playbook을 그룹핑해서 반환한다."""
    categories: dict[str, list[Playbook]] = {}
    for pb in _playbooks.values():
        categories.setdefault(pb.category, []).append(pb)
    return categories
