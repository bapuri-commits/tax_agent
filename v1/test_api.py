"""V1 API 수동 테스트 스크립트."""

import json
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://localhost:8000/api/v1/skill/message"


def send(utterance: str, user_id: str = "test_001") -> dict:
    body = {"userRequest": {"utterance": utterance, "user": {"id": user_id}}}
    r = requests.post(BASE, json=body)
    return r.json()


def pp(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    print("=== 1. 처음으로 (인사) ===")
    pp(send("처음으로"))
    print()

    print("=== 2. 주민등록 카테고리 ===")
    pp(send("주민등록"))
    print()

    print("=== 3. 전입신고 선택 ===")
    pp(send("전입신고"))
    print()

    print("=== 4. 본인 선택 (조건 응답) ===")
    pp(send("self"))
    print()

    print("=== 5. 자유 입력 (새 유저) ===")
    pp(send("이사했는데 주소 바꿔야해요", "test_002"))
