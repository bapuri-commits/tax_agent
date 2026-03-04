# 성북구청 카카오톡 민원 상담 챗봇 — 설계 문서

## 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [V1: 강화형 전통 챗봇](#v1-강화형-전통-챗봇)
3. [V2: AI 도입 챗봇](#v2-ai-도입-챗봇)
4. [공통 인프라](#공통-인프라)
5. [개발 로드맵](#개발-로드맵)

---

## 프로젝트 개요

성북구청 카카오톡 민원 상담 챗봇을 **두 단계로 구축**한다.

- **V1**은 기존 자치구 챗봇(광진구 등) 수준의 메뉴/키워드 기반 챗봇이되, 응답 품질과 커버리지를 강화한 버전이다.
- **V2**는 LLM + RAG를 도입하여 자연어 상담이 가능한 AI 챗봇이다.

V1을 먼저 완성하면:
- 민원 데이터(Playbook, FAQ, 링크)가 축적되어 V2의 RAG/학습 데이터로 직접 재활용된다.
- 카카오 오픈빌더 연동, 응답 포맷, 배포 파이프라인 등 공통 인프라가 검증된다.
- V2 전환 시 백엔드 로직만 교체하면 되므로 리스크가 낮다.

### 두 버전 비교

| 구분 | V1: 강화형 전통 챗봇 | V2: AI 도입 챗봇 |
|------|----------------------|-------------------|
| 대화 방식 | 버튼 메뉴 + 키워드 매칭 | 자연어 입력 + LLM 의도 분류 |
| 답변 생성 | 미리 작성된 정적 응답 | Playbook + RAG + LLM 조합 |
| 추가 정보 수집 | 고정 폼 / 버튼 선택지 | 동적 슬롯 필링 (대화형) |
| LLM 사용 | 없음 | 의도 분류, 후속 질문, 응답 정리 |
| RAG | 없음 (정적 링크 매핑) | pgvector 기반 벡터 검색 |
| 월 운영비 | 서버비만 (~₩5만 이하) | 서버비 + LLM API (~₩20~50만) |
| 개발 난이도 | 낮음 | 높음 |
| 유지보수 | 수동 업데이트 | 반자동 (크롤링 + 재인덱싱) |

---

## V1: 강화형 전통 챗봇

### 설계 철학

LLM 없이, **메뉴 탐색 + 키워드 검색 + 정적 응답**만으로 민원 안내를 처리한다.
기존 자치구 챗봇 대비 강화 포인트:

1. **넓은 커버리지**: 상위 30개 민원 유형 전부 대응
2. **구조화된 응답**: 결론 → 필요서류 → 링크 → 담당부서 통일 포맷
3. **2단계 키워드 검색**: 카테고리 매칭 실패 시 키워드 유사도 검색으로 폴백
4. **에스컬레이션**: 매칭 실패 시 담당부서 직접 안내 (방치하지 않음)

### 아키텍처

```
[사용자] → [카카오톡]
               ↓
         [카카오 오픈빌더]
          - 시나리오 블록 (메뉴 버튼)
          - 폴백 블록 → 스킬 서버 호출
               ↓
         [FastAPI 스킬 서버]
          - 키워드 매칭 엔진
          - FAQ 검색
          - 정적 응답 조회
          - 응답 포매터
               ↓
         [데이터 저장소]
          - Playbook JSON 파일
          - FAQ DB (SQLite/PostgreSQL)
          - 대화 로그 DB
```

### 대화 흐름

```
사용자: (카카오톡 진입)
  ↓
봇: 안녕하세요! 성북구청 민원 상담입니다.
    아래에서 원하시는 분야를 선택해주세요.
    [주민등록] [세금/납부] [복지/지원] [주차/교통]
    [쓰레기/환경] [건축/도시] [증명서발급] [기타문의]
  ↓
사용자: [주민등록] 클릭
  ↓
봇: 주민등록 관련 어떤 업무가 필요하신가요?
    [전입신고] [전출신고] [등본발급] [인감등록] [기타]
  ↓
사용자: [전입신고] 클릭
  ↓
봇: (해당 Playbook의 조건 분기 시작)
    전입신고 대상자를 선택해주세요.
    [본인] [세대원(가족)] [대리인]
  ↓
사용자: [본인] 클릭
  ↓
봇: ✅ 본인 전입신고 안내
    
    📌 준비물
    - 신분증 (주민등록증 또는 운전면허증)
    - 전입지 확인 서류 (임대차계약서 등)
    
    📄 신청 방법
    - 온라인: 정부24 (gov.kr)
    - 방문: 성북구청 민원실 (1층)
    
    🔗 바로가기
    - 정부24 전입신고: https://...
    - 성북구청 민원안내: https://...
    
    🏢 담당부서: 주민센터 민원팀 (02-XXX-XXXX)
    
    [처음으로] [다른 질문하기]
```

**폴백 흐름 (자유 입력 시)**:

```
사용자: "전입신고 어떻게 해요?"
  ↓
스킬 서버:
  1. 키워드 추출: "전입신고"
  2. Playbook 키워드 매칭: "전입신고" → move_in playbook
  3. 매칭 성공 → 해당 Playbook 응답 반환
  
  매칭 실패 시:
  1. FAQ DB 유사도 검색 (TF-IDF 또는 단순 키워드 매칭)
  2. 검색 결과 있으면 → FAQ 답변 반환
  3. 검색 결과 없으면 → "죄송합니다. 해당 문의는 [종합민원실 02-XXX-XXXX]로 연락 부탁드립니다."
```

### 스킬 서버 API

```
POST /api/v1/skill/message
  - 카카오 오픈빌더 스킬 요청 수신
  - 시나리오 블록에서 넘어온 파라미터 또는 자유 입력 텍스트 처리
  - SkillResponse JSON 반환

POST /api/v1/skill/button-action
  - 버튼 클릭 이벤트 처리 (Playbook 조건 분기)
  - 다음 질문 또는 최종 응답 반환
```

### V1 Playbook 스키마

```json
{
  "id": "move_in",
  "name": "전입신고",
  "category": "주민등록",
  "keywords": ["전입", "전입신고", "이사", "주소변경", "주소이전"],
  "conditions": [
    {
      "question": "전입신고 대상자를 선택해주세요.",
      "param": "applicant_type",
      "options": [
        {"label": "본인", "value": "self"},
        {"label": "세대원(가족)", "value": "family"},
        {"label": "대리인", "value": "proxy"}
      ]
    }
  ],
  "responses": {
    "self": {
      "conclusion": "본인 전입신고 안내",
      "documents": ["신분증", "전입지 확인 서류(임대차계약서 등)"],
      "methods": {
        "online": {"name": "정부24", "url": "https://www.gov.kr/..."},
        "offline": "성북구청 민원실 1층 또는 관할 주민센터"
      },
      "links": [
        {"title": "정부24 전입신고", "url": "https://..."},
        {"title": "성북구청 민원안내", "url": "https://..."}
      ],
      "department": {
        "name": "주민센터 민원팀",
        "phone": "02-XXX-XXXX"
      }
    },
    "family": { "..." : "..." },
    "proxy": { "..." : "..." }
  }
}
```

### V1 폴더 구조

```
tax_agent/
├── DESIGN.md
├── v1/
│   ├── app/
│   │   ├── main.py              # FastAPI 진입점
│   │   ├── config.py            # 환경설정
│   │   ├── routers/
│   │   │   ├── skill.py         # 카카오 스킬 엔드포인트
│   │   │   └── admin.py         # 관리용 API (Playbook CRUD)
│   │   ├── services/
│   │   │   ├── matcher.py       # 키워드 매칭 엔진
│   │   │   ├── playbook.py      # Playbook 로딩/조회
│   │   │   ├── faq.py           # FAQ 검색
│   │   │   └── formatter.py     # 카카오 SkillResponse 포매터
│   │   ├── models/
│   │   │   ├── kakao.py         # 카카오 요청/응답 Pydantic 모델
│   │   │   └── playbook.py      # Playbook Pydantic 모델
│   │   └── data/
│   │       └── playbooks/       # Playbook JSON 파일들
│   │           ├── move_in.json
│   │           ├── parking.json
│   │           └── ...
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
```

### V1 기술 스택

| 구성 | 선택 | 이유 |
|------|------|------|
| 서버 | FastAPI | 카카오 스킬 서버에 적합, 비동기, Pydantic 내장 |
| 데이터 | JSON 파일 + SQLite | Playbook은 JSON, FAQ/로그는 SQLite. 소규모에 충분 |
| 검색 | 키워드 매칭 (Komoran/Kiwi) | 한국어 형태소 분석 기반 키워드 추출 |
| 배포 | Docker + 클라우드 VM | 단일 컨테이너로 충분 |

---

## V2: AI 도입 챗봇

### 설계 철학

V1의 Playbook 데이터를 그대로 활용하되, **자연어 이해 + 동적 대화 + RAG 지식 보강**을 추가한다.

핵심 원칙:
1. **LLM은 보조 도구**: 판단은 Playbook 룰 엔진, LLM은 이해/표현만 담당
2. **할루시네이션 제로**: 정책 정보는 반드시 RAG 검색 결과 또는 Playbook에서 인용
3. **비용 통제**: LLM 호출은 세션당 최대 3회 이내 목표

### 아키텍처

```
[사용자] → [카카오톡]
               ↓
         [카카오 오픈빌더]
          - 자유 입력 수신 → 스킬 서버 전달
          - 버튼 응답 렌더링
          - 비동기 응답은 Callback 처리
               ↓
         [FastAPI 백엔드]
          ├─ 세션 매니저 (상태 머신)
          ├─ 의도 분류기 (LLM 호출 #1)
          ├─ 슬롯 필링 엔진 (LLM 호출 #2, 선택적)
          ├─ Playbook 룰 엔진 (결정 로직, LLM 없음)
          ├─ RAG 검색기 (pgvector)
          ├─ 응답 생성기 (LLM 호출 #3, 선택적)
          └─ 에스컬레이션 핸들러
               ↓
         [데이터 레이어]
          ├─ PostgreSQL
          │   ├─ sessions / users / logs
          │   ├─ playbooks (JSON 컬럼)
          │   └─ pgvector (임베딩 저장)
          └─ Redis (세션 캐시, 의도 분류 캐시)
```

### 상태 머신

```
         ┌─────────────────────────────────────────┐
         │                                         │
         ▼                                         │
       IDLE ──→ INTENT_CLASSIFYING ──→ SLOT_FILLING ──→ CASE_DETERMINED ──→ RESPONSE_READY ──→ COMPLETED
                       │                    │                                      │
                       │                    │                                      │
                       ▼                    ▼                                      ▼
                  FALLBACK_SEARCH      ESCALATED                              ESCALATED
                       │
                       ▼
                  ESCALATED
```

| 상태 | 진입 조건 | 처리 | 전이 |
|------|-----------|------|------|
| IDLE | 세션 시작 또는 이전 상담 완료 | 인사 메시지 표시 | 사용자 입력 → INTENT_CLASSIFYING |
| INTENT_CLASSIFYING | 사용자 자연어 입력 수신 | LLM으로 의도 분류, Playbook 매칭 | 매칭 성공 → SLOT_FILLING / 실패 → FALLBACK_SEARCH |
| SLOT_FILLING | Playbook 확정, 필수 슬롯 미수집 | 부족한 슬롯에 대해 질문 생성 | 슬롯 완료 → CASE_DETERMINED / 3회 실패 → ESCALATED |
| CASE_DETERMINED | 필수 슬롯 모두 수집 | Playbook decision_rules 평가 | 규칙 매칭 → RESPONSE_READY / 미매칭 → ESCALATED |
| RESPONSE_READY | 결정 완료 | RAG로 링크 보강 + LLM으로 응답 정리 | 응답 전송 → COMPLETED |
| FALLBACK_SEARCH | 의도 분류 실패 | RAG 검색으로 유사 FAQ 탐색 | 결과 있음 → RESPONSE_READY / 없음 → ESCALATED |
| ESCALATED | 자동 처리 불가 판단 | 담당부서 정보 + 전화번호 안내 | → COMPLETED |
| COMPLETED | 응답 전송 완료 | 만족도 조사 + 추가 문의 버튼 | 추가 문의 → IDLE / 종료 |

### V2 Playbook 스키마 (V1 확장)

```json
{
  "id": "move_in",
  "name": "전입신고",
  "category": "주민등록",
  "keywords": ["전입", "전입신고", "이사", "주소변경"],
  "intent_examples": [
    "전입신고 하고 싶어요",
    "이사했는데 주소 바꿔야 해요",
    "다른 구에서 성북구로 이사왔어요"
  ],
  "required_slots": [
    {
      "name": "applicant_type",
      "question": "전입신고 대상자가 누구인가요?",
      "type": "choice",
      "options": ["본인", "세대원(가족)", "대리인"],
      "required": true
    },
    {
      "name": "has_contract",
      "question": "임대차계약서를 가지고 계신가요?",
      "type": "boolean",
      "required": true
    }
  ],
  "decision_rules": [
    {
      "condition": {"applicant_type": "self", "has_contract": true},
      "response_key": "self_with_contract"
    },
    {
      "condition": {"applicant_type": "self", "has_contract": false},
      "response_key": "self_without_contract"
    },
    {
      "condition": {"applicant_type": "proxy"},
      "response_key": "proxy"
    }
  ],
  "responses": {
    "self_with_contract": {
      "conclusion": "본인 전입신고가 가능합니다.",
      "documents": ["신분증", "임대차계약서"],
      "methods": {
        "online": {"name": "정부24", "url": "https://www.gov.kr/..."},
        "offline": "성북구청 민원실 1층 또는 관할 주민센터"
      },
      "department": {"name": "주민센터 민원팀", "phone": "02-XXX-XXXX"}
    }
  },
  "escalation_conditions": [
    "외국인 전입",
    "재외국민 등록",
    "슬롯 수집 3회 실패"
  ],
  "official_links": [
    {"title": "정부24 전입신고", "url": "https://..."},
    {"title": "성북구청 민원안내", "url": "https://..."}
  ]
}
```

### V2 LLM 호출 정책

| 호출 시점 | 모델 | 입력 | 출력 | 예상 토큰 |
|-----------|------|------|------|-----------|
| 의도 분류 | gpt-4o-mini | 사용자 발화 + Playbook 목록 | playbook_id 또는 "unknown" | ~300 |
| 슬롯 추출 | gpt-4o-mini | 사용자 발화 + 필요 슬롯 목록 | 추출된 슬롯 값 JSON | ~200 |
| 응답 정리 | gpt-4o-mini | Playbook 응답 원문 + RAG 결과 | 자연스러운 안내 텍스트 | ~500 |

**비용 통제 규칙:**
- 세션당 LLM 호출 최대 3회
- 의도 분류 결과는 Redis 캐시 (TTL 24h), 동일 발화 패턴 재사용
- Playbook 키워드 매칭이 성공하면 LLM 의도 분류 스킵
- 응답 정리는 선택적 — Playbook 정적 응답만으로 충분하면 스킵

### V2 RAG 파이프라인

```
[데이터 소스]                    [인제스천]                    [저장]
성북구청 홈페이지 ──┐
구정 FAQ 페이지   ──┼──→ 크롤러 ──→ HTML/PDF 파서 ──→ 청크 분할 ──→ 임베딩 ──→ pgvector
민원 안내 PDF     ──┘    (주 1회)    (BeautifulSoup)   (페이지 단위)  (multilingual-e5)

[검색 흐름]
사용자 질문 ──→ 임베딩 ──→ pgvector 유사도 검색 (top-3) ──→ 결과 + 출처 URL 반환
```

**청크 전략:**
- 성북구 공식 페이지는 대부분 짧은 안내문이므로 **페이지 단위** 청킹이 기본
- 긴 PDF는 **섹션/제목 기준** 분할 (500자 이내)

**임베딩 모델:** `multilingual-e5-large` (한국어 성능 우수, 오픈소스)

### V2 DB 스키마

```sql
-- 사용자 (카카오 식별자 기반)
CREATE TABLE users (
    id            SERIAL PRIMARY KEY,
    kakao_user_id VARCHAR(100) UNIQUE NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- 상담 세션
CREATE TABLE sessions (
    id              SERIAL PRIMARY KEY,
    user_id         INT REFERENCES users(id),
    playbook_id     VARCHAR(50),
    current_state   VARCHAR(30) NOT NULL DEFAULT 'IDLE',
    slot_values     JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- 대화 로그
CREATE TABLE conversation_logs (
    id          SERIAL PRIMARY KEY,
    session_id  INT REFERENCES sessions(id),
    role        VARCHAR(10) NOT NULL,  -- 'user' | 'bot'
    content     TEXT NOT NULL,
    metadata    JSONB DEFAULT '{}',    -- LLM 호출 여부, 토큰 수, 소요시간 등
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- RAG 문서 임베딩
CREATE TABLE documents (
    id          SERIAL PRIMARY KEY,
    source_url  TEXT NOT NULL,
    title       TEXT,
    content     TEXT NOT NULL,
    embedding   vector(1024),
    updated_at  TIMESTAMPTZ DEFAULT now()
);
```

### V2 폴더 구조

```
tax_agent/
├── DESIGN.md
├── v2/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── routers/
│   │   │   ├── skill.py           # 카카오 스킬 엔드포인트
│   │   │   └── admin.py           # 관리 API
│   │   ├── services/
│   │   │   ├── session.py         # 상태 머신 + 세션 관리
│   │   │   ├── intent.py          # 의도 분류 (키워드 → LLM 폴백)
│   │   │   ├── slot_filler.py     # 슬롯 수집 엔진
│   │   │   ├── rule_engine.py     # Playbook 결정 규칙 평가
│   │   │   ├── rag.py             # RAG 검색
│   │   │   ├── llm.py             # LLM 클라이언트 (호출 제한 포함)
│   │   │   ├── formatter.py       # 카카오 SkillResponse 포매터
│   │   │   └── escalation.py      # 에스컬레이션 핸들러
│   │   ├── models/
│   │   │   ├── kakao.py
│   │   │   ├── session.py
│   │   │   └── playbook.py
│   │   └── data/
│   │       └── playbooks/
│   ├── rag/
│   │   ├── crawler.py             # 성북구청 페이지 크롤러
│   │   ├── parser.py              # HTML/PDF 파서
│   │   ├── chunker.py             # 청크 분할
│   │   ├── embedder.py            # 임베딩 생성
│   │   └── indexer.py             # pgvector 인덱싱
│   ├── tests/
│   ├── docker-compose.yml         # FastAPI + PostgreSQL + Redis
│   └── requirements.txt
```

---

## 공통 인프라

V1과 V2가 **공유하는 부분**을 명확히 해서, V1 → V2 전환 비용을 최소화한다.

### 공유 자산

| 자산 | 설명 |
|------|------|
| **Playbook 데이터** | V1의 JSON을 V2에서 그대로 사용 (V2는 `intent_examples`, `required_slots` 등 필드 추가) |
| **카카오 SkillResponse 포매터** | 응답 JSON 생성 로직은 동일 |
| **카카오 오픈빌더 설정** | 스킬 서버 URL만 변경하면 V2로 전환 가능 |
| **응답 템플릿** | 결론 → 준비물 → 신청방법 → 링크 → 담당부서 포맷 통일 |

### 카카오 SkillResponse 포맷 (공통)

```json
{
  "version": "2.0",
  "template": {
    "outputs": [
      {
        "textCard": {
          "title": "✅ 본인 전입신고 안내",
          "description": "📌 준비물\n- 신분증\n- 임대차계약서\n\n📄 신청방법\n- 온라인: 정부24\n- 방문: 성북구청 민원실 1층",
          "buttons": [
            {"label": "정부24 바로가기", "action": "webLink", "webLinkUrl": "https://..."},
            {"label": "담당부서 전화", "action": "phone", "phoneNumber": "02-XXX-XXXX"},
            {"label": "처음으로", "action": "block", "blockId": "BLOCK_ID"}
          ]
        }
      }
    ]
  }
}
```

---

## 개발 로드맵

### Phase 1: V1 MVP (4~6주)

| 주차 | 작업 |
|------|------|
| 1주 | Playbook 스키마 확정 + 상위 10개 민원 유형 데이터 작성 |
| 2주 | FastAPI 스킬 서버 뼈대 + 카카오 오픈빌더 연동 |
| 3주 | 키워드 매칭 엔진 + 응답 포매터 구현 |
| 4주 | 나머지 20개 민원 유형 데이터 + FAQ 검색 |
| 5~6주 | 테스트 + 배포 + 카카오 심사 |

### Phase 2: V2 전환 (6~8주)

| 주차 | 작업 |
|------|------|
| 1~2주 | PostgreSQL + pgvector 세팅 + RAG 크롤러/인덱서 |
| 3~4주 | 상태 머신 + 세션 관리 + LLM 의도 분류 |
| 5~6주 | 슬롯 필링 + 룰 엔진 + 응답 생성 |
| 7~8주 | 통합 테스트 + 비용 모니터링 + V2 전환 배포 |

### Phase 3: 고도화 (이후)

- 대화 만족도 피드백 수집 및 분석
- Playbook 자동 업데이트 (크롤링 기반)
- 다국어 지원 (영어, 중국어)
- 음성 입력 대응
