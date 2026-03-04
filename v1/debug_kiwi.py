"""실패한 테스트 케이스의 Kiwi 분석 결과를 상세 확인."""
import sys
sys.stdout.reconfigure(encoding="utf-8")

from kiwipiepy import Kiwi
kiwi = Kiwi()

TARGET_POS = {"NNG", "NNP", "NNB", "VV", "VA", "SL"}

failed = [
    "다른 지역으로 이사 나갈 건데요",
    "재산세 얼마인지 알고 싶어요",
    "아이 수당 언제 나오나요",
    "소파 버리려고 하는데요",
    "냉장고 버리는 방법",
]

for text in failed:
    tokens = kiwi.tokenize(text)
    print(f"입력: '{text}'")
    print(f"  전체 토큰: {[(t.form, t.tag) for t in tokens]}")
    extracted = [t.form for t in tokens if t.tag in TARGET_POS]
    print(f"  추출된 키워드: {extracted}")
    print()
