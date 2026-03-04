"""카카오 SkillResponse 포매터.

Playbook 데이터를 카카오톡 응답 JSON으로 변환한다.
모든 응답은 동일한 구조를 따른다:
  ✅ 결론 → 📌 준비물 → 📄 신청방법 → 🔗 링크 → 🏢 담당부서
"""

from __future__ import annotations

from app.models.kakao import (
    Button,
    KakaoSkillResponse,
    QuickReply,
    SimpleText,
    SimpleTextOutput,
    SkillTemplate,
    TextCard,
    TextCardOutput,
)
from app.models.playbook import Condition, Playbook, PlaybookResponse
from app.services.playbook import get_categories

TEXTCARD_DESC_MAX_LEN = 380


def build_greeting() -> KakaoSkillResponse:
    """첫 인사 메시지. 카테고리는 로드된 Playbook 기준으로 동적 생성."""
    categories = get_categories()
    quick_replies = [
        QuickReply(label=cat, messageText=cat)
        for cat in sorted(categories.keys())
    ]

    return KakaoSkillResponse(
        template=SkillTemplate(
            outputs=[
                SimpleTextOutput(
                    simpleText=SimpleText(
                        text=(
                            "안녕하세요! 성북구청 민원 상담 챗봇입니다.\n\n"
                            "아래에서 원하시는 분야를 선택하시거나,\n"
                            "궁금한 내용을 직접 입력해주세요."
                        )
                    )
                )
            ],
            quickReplies=quick_replies if quick_replies else None,
        )
    )


def build_category_menu(category: str, playbooks: list[Playbook]) -> KakaoSkillResponse:
    """카테고리 내 민원 유형 목록을 QuickReply로 표시."""
    return KakaoSkillResponse(
        template=SkillTemplate(
            outputs=[
                SimpleTextOutput(
                    simpleText=SimpleText(
                        text=f"[{category}] 관련 어떤 업무가 필요하신가요?"
                    )
                )
            ],
            quickReplies=[
                QuickReply(label=pb.name, messageText=pb.name)
                for pb in playbooks
            ]
            + [QuickReply(label="처음으로", messageText="처음으로")],
        )
    )


def build_condition_question(playbook: Playbook, condition: Condition) -> KakaoSkillResponse:
    """Playbook의 조건 분기 질문을 QuickReply로 표시."""
    return KakaoSkillResponse(
        template=SkillTemplate(
            outputs=[
                SimpleTextOutput(
                    simpleText=SimpleText(
                        text=f"[{playbook.name}]\n\n{condition.question}"
                    )
                )
            ],
            quickReplies=[
                QuickReply(label=opt.label, messageText=opt.value)
                for opt in condition.options
            ],
        )
    )


def _truncate_description(text: str, max_len: int = TEXTCARD_DESC_MAX_LEN) -> str:
    """TextCard description이 카카오 제한을 넘지 않도록 자른다."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def build_final_response(playbook: Playbook, response: PlaybookResponse) -> KakaoSkillResponse:
    """최종 답변을 TextCard로 구성."""
    lines = []

    if response.documents:
        lines.append("📌 준비물")
        for doc in response.documents:
            lines.append(f"  • {doc}")
        lines.append("")

    if response.methods:
        lines.append("📄 신청 방법")
        for method in response.methods.values():
            if method.url:
                lines.append(f"  • {method.name}")
            elif method.address:
                lines.append(f"  • {method.name}: {method.address}")
        lines.append("")

    lines.append(f"🏢 담당부서: {response.department.name}")
    lines.append(f"☎ {response.department.phone}")

    buttons: list[Button] = []
    for link in response.links[:3]:
        buttons.append(
            Button(label=link.title[:14], action="webLink", webLinkUrl=link.url)
        )
    buttons.append(
        Button(
            label="담당부서 전화",
            action="phone",
            phoneNumber=response.department.phone,
        )
    )

    return KakaoSkillResponse(
        template=SkillTemplate(
            outputs=[
                TextCardOutput(
                    textCard=TextCard(
                        title=f"✅ {response.conclusion}",
                        description=_truncate_description("\n".join(lines)),
                        buttons=buttons,
                    )
                )
            ],
            quickReplies=[
                QuickReply(label="처음으로", messageText="처음으로"),
                QuickReply(label="다른 질문하기", messageText="다른 질문하기"),
            ],
        )
    )


def build_fallback() -> KakaoSkillResponse:
    """매칭 실패 시 안내 메시지."""
    return KakaoSkillResponse(
        template=SkillTemplate(
            outputs=[
                SimpleTextOutput(
                    simpleText=SimpleText(
                        text=(
                            "죄송합니다. 해당 문의를 정확히 파악하지 못했습니다.\n\n"
                            "아래 방법으로 문의해주시면 빠르게 도움드리겠습니다.\n\n"
                            "📞 성북구청 종합민원실: 02-2241-2114\n"
                            "🌐 성북구청 홈페이지: https://www.sb.go.kr"
                        )
                    )
                )
            ],
            quickReplies=[
                QuickReply(label="처음으로", messageText="처음으로"),
            ],
        )
    )
