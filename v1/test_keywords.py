"""키워드 유효성 강도 높은 검증 스크립트.

검증 항목:
  1. 모든 Playbook 키워드가 Kiwi 형태소 분석으로 추출 가능한지
  2. 키워드 충돌 (같은 키워드가 여러 Playbook에 걸리는 경우)
  3. 실제 사용자 발화 시뮬레이션 → 올바른 Playbook 매칭 여부
  4. 의도적 오매칭 테스트 (엉뚱한 입력에 매칭되면 안 되는 경우)
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))

from kiwipiepy import Kiwi

kiwi = Kiwi()

PLAYBOOK_DIR = Path(__file__).parent / "app" / "data" / "playbooks"

TARGET_POS = {"NNG", "NNP", "NNB", "VV", "VA", "SL"}


def load_all_playbooks():
    playbooks = {}
    for path in sorted(PLAYBOOK_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            playbooks[path.stem] = json.load(f)
    return playbooks


def extract_keywords(text):
    tokens = kiwi.tokenize(text)
    return [t.form for t in tokens if t.tag in TARGET_POS]


def build_keyword_index(playbooks):
    index = {}
    for pb_id, pb in playbooks.items():
        for kw in pb["keywords"]:
            index.setdefault(kw, []).append(pb_id)
    return index


def match(text, playbooks, keyword_index):
    user_kws = extract_keywords(text)
    scores = {}

    for uk in user_kws:
        if uk in keyword_index:
            for pb_id in keyword_index[uk]:
                if pb_id not in scores:
                    scores[pb_id] = (0.0, [])
                s, m = scores[pb_id]
                m.append(uk)
                scores[pb_id] = (s + 1.0, m)

    if not scores:
        for pb_id, pb in playbooks.items():
            matched = [kw for kw in pb["keywords"] if kw in text]
            if matched:
                scores[pb_id] = (len(matched) * 0.5, matched)

    if not scores:
        return None, [], []

    best_id = max(scores, key=lambda k: scores[k][0])
    return best_id, scores[best_id][1], user_kws


# ============================================================
# 검증 실행
# ============================================================
playbooks = load_all_playbooks()
keyword_index = build_keyword_index(playbooks)

print(f"로드된 Playbook: {len(playbooks)}개")
print(f"전체 키워드 수: {sum(len(pb['keywords']) for pb in playbooks.values())}개")
print()

# ── 검증 1: 키워드 충돌 분석 ──
print("=" * 60)
print("검증 1: 키워드 충돌 (같은 키워드 → 여러 Playbook)")
print("=" * 60)
conflicts = {kw: pbs for kw, pbs in keyword_index.items() if len(pbs) > 1}
if conflicts:
    for kw, pbs in conflicts.items():
        print(f"  ⚠ '{kw}' → {pbs}")
else:
    print("  ✅ 충돌 없음")
print()

# ── 검증 2: 키워드 Kiwi 추출 가능성 ──
print("=" * 60)
print("검증 2: 각 키워드가 Kiwi 형태소 분석으로 추출 가능한지")
print("=" * 60)
not_extractable = []
for pb_id, pb in playbooks.items():
    for kw in pb["keywords"]:
        tokens = kiwi.tokenize(kw)
        forms = [t.form for t in tokens]
        extracted = extract_keywords(kw)
        if kw not in extracted and kw not in " ".join(forms):
            not_extractable.append((pb_id, kw, forms, extracted))

if not_extractable:
    for pb_id, kw, forms, extracted in not_extractable:
        print(f"  ⚠ [{pb_id}] '{kw}' → 분석: {forms} / 추출: {extracted}")
else:
    print("  ✅ 모든 키워드 추출 가능")
print()

# ── 검증 3: 키워드별 형태소 분석 상세 ──
print("=" * 60)
print("검증 3: 키워드별 Kiwi 분석 상세 (1단계 정확매칭 가능 여부)")
print("=" * 60)
for pb_id, pb in playbooks.items():
    print(f"\n  [{pb_id}] {pb['name']}")
    for kw in pb["keywords"]:
        tokens = kiwi.tokenize(kw)
        detail = [(t.form, t.tag) for t in tokens]
        extracted = extract_keywords(kw)
        in_index = "✅" if kw in extracted else "⚠ 부분문자열 폴백"
        print(f"    '{kw}' → {detail} → 추출: {extracted} {in_index}")
print()

# ── 검증 4: 실제 사용자 발화 시뮬레이션 ──
print("=" * 60)
print("검증 4: 실제 사용자 발화 매칭 테스트")
print("=" * 60)

test_cases = [
    # (입력, 기대 Playbook ID)
    # 주민등록
    ("전입신고 하려고요", "move_in"),
    ("이사왔는데 주소 옮겨야해요", "move_in"),
    ("다른 구에서 성북구로 이사했어요", "move_in"),
    ("전출신고 하고싶어요", "move_out"),
    ("다른 지역으로 이사 나갈 건데요", "move_out"),

    # 세금
    ("재산세 얼마인지 알고 싶어요", "local_tax"),
    ("자동차세 납부하려고요", "local_tax"),
    ("세금 고지서 왔는데 어떻게 내요?", "local_tax"),
    ("지방세 납부 방법 알려주세요", "local_tax"),
    ("취득세 신고해야 돼요", "local_tax"),

    # 복지
    ("기초생활수급자 신청하려면요", "basic_livelihood"),
    ("생계급여 받고 싶어요", "basic_livelihood"),
    ("수급자 자격이 되는지 궁금해요", "basic_livelihood"),
    ("아동수당 신청하려고요", "child_allowance"),
    ("아이 수당 언제 나오나요", "child_allowance"),

    # 증명서
    ("등본 떼러 왔어요", "resident_certificate"),
    ("주민등록등본 발급해주세요", "resident_certificate"),
    ("초본 필요한데요", "resident_certificate"),
    ("가족관계증명서 발급하고 싶어요", "family_certificate"),
    ("혼인관계증명서 어디서 발급하나요", "family_certificate"),

    # 쓰레기/환경
    ("소파 버리려고 하는데요", "bulky_waste"),
    ("대형폐기물 스티커 어디서 사나요", "bulky_waste"),
    ("냉장고 버리는 방법", "bulky_waste"),
    ("매트리스 어떻게 버려요", "bulky_waste"),
    ("층간소음 너무 심한데 신고하고 싶어요", "noise_complaint"),
    ("위층에서 밤에 시끄러운데 어디다 말해요", "noise_complaint"),
    ("공사 소음이 너무 시끄러워요", "noise_complaint"),

    # 주차
    ("불법주차 신고하려고요", "parking_violation"),
    ("앞에 이중주차 해놨어요", "parking_violation"),
    ("거주자 우선주차 신청하려고요", "resident_parking"),
    ("우리 아파트 앞 주차구획 신청", "resident_parking"),
]

pass_count = 0
fail_count = 0
for utterance, expected in test_cases:
    matched_id, matched_kws, user_kws = match(utterance, playbooks, keyword_index)
    status = "✅" if matched_id == expected else "❌"
    if matched_id == expected:
        pass_count += 1
    else:
        fail_count += 1
    print(f"  {status} '{utterance}'")
    print(f"      형태소: {user_kws}")
    print(f"      매칭: {matched_id} (키워드: {matched_kws})")
    if matched_id != expected:
        print(f"      ❌ 기대: {expected}")
    print()

print(f"결과: {pass_count}/{len(test_cases)} 통과, {fail_count}개 실패")
print()

# ── 검증 5: 오매칭 테스트 (매칭되면 안 되는 입력) ──
print("=" * 60)
print("검증 5: 오매칭 테스트 (매칭되면 안 되는 무관한 입력)")
print("=" * 60)

false_inputs = [
    "오늘 날씨 어때?",
    "점심 뭐 먹을까",
    "구청장 누구야",
    "성북구 인구 몇 명이야",
    "안녕하세요",
    "ㅋㅋㅋ",
]
for utterance in false_inputs:
    matched_id, matched_kws, user_kws = match(utterance, playbooks, keyword_index)
    if matched_id is None:
        print(f"  ✅ '{utterance}' → 매칭 없음 (정상)")
    else:
        print(f"  ⚠ '{utterance}' → {matched_id} (오매칭! 키워드: {matched_kws})")
    print()
