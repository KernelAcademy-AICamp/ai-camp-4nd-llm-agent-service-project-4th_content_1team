# Project Process Guideline & Architecture

## 1. 스크립트 단계

### 1. 주제 해석/브리프 생성 Planner 에이전트

**인풋**
*   **주제**
*   **채널 프로필** (카테고리, 타겟 시청자층, 평균 영상 길이)
*   **최근 10개 영상에서 자주 쓰는 포맷**: 리스트형/스토리형/튜토리얼형 (이미 채널이 있다면)
    *   *시청자 반응(댓글에서 반복되는 질문/불만) (이미 채널이 있다면)*
*   **앵글 (Angle) 설정**
    *   **앵글 A (정보 전달형)**: 최신 뉴스 팩트 중심의 신뢰도 높은 구성
    *   **앵글 B (비판/논란형)**: 기존 영상들과 반대되는 통찰력을 제시하는 도발적 구성
    *   **앵글 C (스토리텔링형)**: 시청자의 공감을 유도하는 경험 중심 구성

**아웃풋**
**ContentBrief (JSON)**
*   `workingTitleCandidates`: 3~5개 + 각 타이틀의 훅 유형, 의도/타겟/톤
*   `coreQuestions`: 이 영상이 답해야 하는 핵심 질문 3~5개
*   `narrative`: 시청 지속을 위한 내러티브 구조 (Hook → Problem → Evidence → Insight → Action)
*   `chapters`: 챕터 리스트 (id, goal, expectedAssets)
*   `researchPlan`: 뉴스 쿼리, 유튜브 검색어, 검색 기간(freshnessDays)

```json
{
  "briefId": "brf_...",
  "topicRequestId": "trq_...",
  "workingTitleCandidates": [
    {"title": "후킹 타이틀 1", "angle": "긴급성/이익/반박"},
    {"title": "후킹 타이틀 2", "angle": "오해 깨기"}
  ],
  "coreQuestions": [
    "이 영상이 답할 질문1",
    "질문2",
    "질문3"
  ],
  "narrative": {
    "hookGoal": "첫 15초에 약속할 가치",
    "structure": ["Hook", "Problem", "Evidence", "Insight", "Action"],
    "chapters": [
      {"id": "c1", "goal": "배경 설명", "expectedAssets": ["기사 스크린샷"]},
      {"id": "c2", "goal": "핵심 근거", "expectedAssets": ["표/수치"]}
    ]
  },
  "researchPlan": {
    "newsQuery": ["키워드 조합1", "키워드 조합2"],
    "competitorQuery": ["유튜브 검색어1", "유튜브 검색어2"],
    "freshnessDays": 60
  }
}
```

**출력 제약**
*   챕터 수 5개 고정 (예: 5±1)
*   챕터마다 "목표 1문장 + 시각자료 1개 타입" 필수
*   뉴스 쿼리: 최소 6개 (기본/반대/사례/통계/용어정의/최신 업데이트)
*   유튜브 쿼리: 최소 4개 (초보용/전문가용/논쟁형/비교형)

**성능 개선 요소**
*   **RAG를 Planner에도 붙이기**: Planner 호출 전에 가볍게라도 최근 뉴스 제목/요약 5~10개를 가져와서 "이 주제에서 지금 핫한 subtopic"을 끼워주면 브리프 퀄리티가 올라갑니다.

---

## 2. 뉴스 수집/본문 추출 Researcher 에이전트

**인풋**
*   키워드들
*   최근 며칠 이내 뉴스만 볼지 (Freshness)
*   지역/언어
*   **검색 방향**
    *   기본 정보 검색: 지금 무슨 일이 벌어지고 있나?
    *   반대/논란 관점 검색: 사람들이 왜 반박하거나 논쟁하나?
    *   통계/데이터 검색: 숫자/리포트/시장 규모 같은 근거가 있나?
    *   사례/케이스 검색: 실제 사례(기업/사람/정책)는 뭔가?
    *   용어 정의 검색: 초보자도 이해할 수 있는 설명이 있나?
*   필요 자료 형태
*   답해야 할 질문

**핵심기능**
1.  소스에서 기사 후보 수집 (RSS/News API/검색 결과)

### *[핵심 전략] Hybrid Trend-Fact Pipeline (Dual Sourcing Ver.)*
*"동시에 긁어서, 서로 빈 곳을 채워준다"*

#### **1. 기본 워크플로우 (Basic Flow)**

**1단계: 동시 수집 (Dual Trigger)**
*   **탐지**: 뉴스(Fact)와 커뮤니티(Trend)를 **처음부터 동시에** 크롤링합니다.
*   **Input**:
    *   **소스 A (뉴스)**: 속보, 통계, 공식 발표 (신뢰도 High, 재미 Low)
    *   **소스 B (커뮤니티)**: 썰, 논란, 실시간 반응 (신뢰도 Low, 재미 High)

**2단계: 상호 연결 (Cross Bridge)**
*   **Type A (팩트 → 재미 보강)**: 딱딱한 경제 뉴스가 잡히면? → **"커뮤니티 반응(댓글)"**을 찾아서 재미를 더합니다.
*   **Type B (썰 → 팩트 검증)**: 자극적인 썰이 잡히면? → **"뉴스 팩트(통계)"**를 찾아서 근거를 뒷받침합니다.

**3단계: 신분 세탁 (Asset Grounding)**
*   **핵심**: 둘 다 긁었으니 **"가장 좋은 자산"**만 골라 씁니다.
*   **Action**: 커뮤니티의 '저화질/불펌 짤'은 폐기하고, 뉴스 기사의 **'고화질 공식 그래프'**나 **'보도자료 사진'**으로 교체(Swap)합니다.

**4단계: 최종 합성 (Hybrid Script)**
*   **Hook**: "커뮤니티에서는 난리 났는데..." (Trend 활용)
*   **Evidence**: "실제 통계(뉴스)를 보니 팩트였습니다." (Fact 활용)
*   **Insight**: "결국 이 현상은 OOO 때문입니다."

---

#### **2. 예외 처리 전략 (Exception Handling)**
*한쪽에만 데이터가 있을 때의 대응 매뉴얼*

**Case A: 뉴스만 있고, 커뮤니티 반응이 없다면? (Early Bird)**
*   **상황**: 중요하지만 재미없어서 아무도 안 떠드는 경우 (실적 발표 등)
*   **판단**: "대중은 아직 모르는 **꿀정보**"
*   **전략**: **"선점 전략 (Be the First)"**
    *   **Script Tone**: "왜 아무도 이걸 모르죠?", "이거 곧 대란 일어납니다" (예언자 포지션)

**Case B: 커뮤니티만 있고, 뉴스 기사가 없다면? (Rumor)**
*   **상황**: 괴담, 단순 유머, 혹은 기자가 아직 안 쓴 방금 터진 떡밥
*   **판단**: "검증되지 않은 **루머**"
*   **전략**: **"참교육/팩트체크 전략 (Debunking)"**
    *   **Action**: 팩트로 단정 짓지 않고 **"의문문"**으로 전환
    *   **Script Tone**: "과연 진짜일까요? 공식 자료는 아직 없습니다.", "판단은 보류해야 합니다." (채널 신뢰도 방어)

---

2.  본문 추출 (readability 기반 파서)
3.  요약/중요 구절 뽑기
4.  이미지/표 자산 수집 (og:image, 본문 img, table html)
5.  청크 저장 (벡터 인덱싱은 선택)

**아웃풋**
**ArticleSet (JSON)**
*   주제 관련 기사 N개 (예: 20개) 메타데이터 + 본문 요약 + 원문 URL
*   클레임(사실 주장) 단위: "A가 B를 했다", "C가 D% 증가"
*   수치/날짜/이용: 표로 정리
*   핵심 근거 문장 위치: 원문 내 문장 스니펫(짧게)
*   이미지/표 추출 가능하면: 기사 내 OG 이미지/대표 이미지 URL, 혹은 본문 이미지 URL 수집
*   표/그래프는 원문에 이미지로 있는 경우 URL로, 텍스트 표면 파싱 가능하면 구조화(HTML table)

```json
{
  "articleSetId": "ars_...",
  "topicRequestId": "trq_...",
  "articles": [
    {
      "articleId": "art_...",
      "source": "publisher|news_api",
      "publisher": "언론사명",
      "url": "https://...",
      "title": "기사 제목",
      "publishedAt": "2026-01-20T12:00:00Z",
      "fetchedAt": "2026-01-21T01:10:00Z",
      "content": {
        "text": "정제된 본문 (전체 저장이 부담이면 요약/스니펫만)",
        "summary": "요약",
        "topQuotes": ["짧은 근거 문장 1", "문장2"]
      },
      "assets": {
        "ogImageUrl": "https://...",
        "imageUrls": ["https://...", "https://..."],
        "tableHtml": ["<table>...</table>"]
      }
    }
  ]
}
```

**신뢰도 검사 (간단 버전)**
1.  동일 팩트가 복수 매체에서 교차 확인되는지
2.  날짜가 너무 오래된 정보인지
3.  1차 출처(공식 리포트/정부/기업 공지) 링크가 있는지

### *[필수 전략] 시각 자료 추출 가이드*
사용자가 호평한 핵심 전략 3가지입니다. 개발 시 반드시 준수해야 합니다.

1.  **"화질은 무조건 원본으로" (High Resolution Only)**
    *   썸네일용 저화질 이미지는 버리고, 클릭해서 나오는 `Largest Image`를 수집합니다.
    *   영상 제작 시 확대해도 깨지지 않도록 원본 링크(`src`)를 확보합니다.

2.  **"복잡한 표는 찰칵 찍어서" (Screenshot over Parsing)**
    *   HTML `<table>` 파싱이 난해하거나 깨지는 경우, 억지로 텍스트로 바꾸지 않습니다.
    *   **Playwright**를 활용해 해당 표 영역(Element)만 깔끔하게 **캡쳐(Screenshot)** 떠서 이미지 에셋으로 저장합니다.

3.  **"증거는 문장 바로 옆에" (Context-Aware Mapping)**
    *   단순히 "이미지 10장"을 나열하지 않습니다.
    *   "이 이미지가 어떤 문장/팩트를 증명하는가?"를 매핑합니다. (JSON의 `assetRefs` 활용)
    *   예: `claim: "매출 2배 증가"` → `asset: "매출_그래프.png"`

### *[기술적 구현 방안]*
*   **Headless Browser 필수**: 동적 렌더링 사이트 대응을 위해 `Playwright` 사용 (Selenium보다 빠르고 스크린샷 기능 강력)
*   **이미지 파싱 우선순위**:
    1.  `data-original`, `data-src` 속성 확인 (Lazy loading 대응)
    2.  `srcset`에서 가장 높은 해상도 URL 파싱
    3.  `src` 속성
*   **표 스크린샷 로직**:
    1.  `table`, `div.chart-container` 등 타겟 요소 식별
    2.  해당 Element에 대해 `element.screenshot()` 메서드 실행
    3.  `padding`을 약간 주어 답답하지 않게 캡쳐


---

## 3. 뉴스 팩트, 시각자료 추출 Agent

**아웃풋 (FactSet JSON)**

```json
{
  "factSetId": "string",
  "topicRequestId": "string",
  "generatedAt": "2026-01-21T00:00:00Z",
  "facts": [
    {
      "factId": "string",
      "type": "stat|event|definition|trend|quote",
      "claim": "string",
      "entities": ["string"],
      "numbers": [
        {
          "value": 0.0,
          "unit": "string",
          "context": "string"
        }
      ],
      "time": {
        "date": "2026-01-20",
        "certainty": "exact|approx|unknown"
      },
      "confidence": 0.0,
      "evidence": [
        {
          "sourceType": "article",
          "articleId": "string",
          "url": "string",
          "publisher": "string",
          "publishedAt": "2026-01-20T12:00:00Z",
          "snippet": "string",
          "locator": {
            "type": "offset|paragraph|unknown",
            "start": 0,
            "end": 0
          },
          "assetRefs": [
            {
              "kind": "og_image|image|table",
              "ref": "string",
              "url": "string"
            }
          ]
        }
      ],
      "tags": ["myth_busting|risk|opportunity|howto|controversy"]
    }
  ],
  "insightSentences": [
    {
      "insightId": "string",
      "sentence": "string",
      "label": "myth_busting|controversy|risk|opportunity|cause_effect|turning_point",
      "whyItMatters": "string",
      "evidence": {
        "articleId": "string",
        "url": "string",
        "snippet": "string"
      }
    }
  ],
  "visualPlan": [
    {
      "visualId": "string",
      "type": "table|chart|timeline|comparison_table",
      "purpose": "string",
      "caption": "string",
      "factIds": ["string"],
      "dataSpec": {
        "columns": ["string"],
        "rows": [["string"]],
        "notes": "string"
      },
      "sourceRefs": [
        {
          "articleId": "string",
          "url": "string"
        }
      ]
    }
  ],
  "dedupe": {
    "clusters": [
      {
        "clusterId": "string",
        "canonicalFactId": "string",
        "mergedFactIds": ["string"],
        "reason": "string"
      }
    ]
  },
  "ranking": {
    "scoringFormulaVersion": "v1",
    "topFactIds": ["string"],
    "explanations": [
      {
        "factId": "string",
        "score": 0.0,
        "reasons": ["string"]
      }
    ]
  },
  "warnings": [
    {
      "type": "low_evidence|stale|single_source|paywalled",
      "message": "string",
      "relatedFactIds": ["string"]
    }
  ]
}
```

---

## 4. 스크립트 검증 & 출처 정리 Verifier 에이전트
*AI가 쓴 스크립트가 거짓말 안 하게 검사하고, 출처 붙이고, 틀리면 고치는 마지막 검사기*

**인풋**
1.  Writer가 쓴 스크립트
2.  Fact Extractor가 만든 팩트 목록
3.  기사 목록(출처용)

**핵심기능**
1.  스크립트에서 사실처럼 보이는 문장들만 골라냄
2.  그 문장이 팩트 데이터에 실제 있는지 확인
3.  있으면 → 출처 연결
4.  없으면 → 삭제하거나 고쳐 씀
5.  최종 "검증된 스크립트"를 만듦

**아웃풋**
1.  검증된 최종 스크립트
2.  문장별 출처 목록
3.  삭제/수정된 문장 리포트

```json
{
  "finalScript": "...",
  "sourceMap": [
    { "sentence": "AI 시장은 40% 성장했다", "source": "00일보" }
  ],
  "removedClaims": [
    "AI 개발자는 모두 연봉 2억이다"
  ]
}
```

## 5. 전체 폴더트리 (Full-Stack Architecture)
*Frontend(완료)와 Backend(LangGraph)가 공존하는 통합 구조입니다.*

```text
root/
├── app/                    # [Frontend] Next.js App Router (완료)
├── components/             # [Frontend] UI Components (완료)
├── public/                 # [Frontend] Static Assets
├── styles/                 # [Frontend] Global Styles
│
├── backend/                # [Backend] Multi-Agent System (Python/LangGraph)
│   ├── src/
│   │   # === [Module 1] 주제 발굴 & 추천 (나경) ===
│   │   ├── topic_rec/
│   │   │   ├── state.py
│   │   │   ├── nodes/
│   │   │   │   ├── persona_analyzer.py
│   │   │   │   ├── video_analyzer.py
│   │   │   │   ├── user_keyword.py
│   │   │   │   ├── trend_crawler.py
│   │   │   │   ├── topic_ranker.py
│   │   │   │   └── final_recommender.py
│   │   │   └── graph.py
│   │
│   │   # === [Module 2] 스크립트 생성 (태윤+빛나) ===
│   │   ├── script_gen/
│   │   │   ├── state.py            # [핵심] OverallState 공유 프로토콜
│   │   │   ├── nodes/
│   │   │   │   ├── planner.py        # (태윤)
│   │   │   │   ├── news_research.py  # (태윤)
│   │   │   │   ├── yt_fetcher.py     # (빛나)
│   │   │   │   ├── fact_extractor.py # (태윤)
│   │   │   │   ├── competitor_anal.py# (빛나)
│   │   │   │   ├── insight_builder.py# (빛나)
│   │   │   │   ├── writer.py         # (빛나)
│   │   │   │   └── verifier.py       # (태윤)
│   │   │   └── graph.py            # 워크플로우 조립
│   │
│   │   # === [Module 3] 썸네일 생성 (도헌) ===
│   │   ├── thumbnail/
│   │   │   ├── nodes/
│   │   │   │   ├── copywriter.py
│   │   │   │   ├── prompt_specialist.py
│   │   │   │   ├── interaction.py
│   │   │   │   ├── art_director.py 
│   │   │   │   └── diffusion.py
│   │   │   └── graph.py
│   │
│   │   # === [공용] ===
│   │   ├── shared/
│   │   │   ├── database.py         # (도헌) DB Schema
│   │   │   ├── authmiddleware.py   # (빛나) OAuth
│   │   │   └── uploader.py         # (빛나) Youtube Upload
│   │   │
│   │   └── main.py                 # (빛나) 통합 서버 엔트리포인트 (FastAPI)
│   │
│   ├── .env
│   └── requirements.txt
│
├── package.json
└── README.md
```

### **협업 가이드 (Protocol)**
1.  **Frontend-Backend 연동**: Frontend(`app/`)는 `backend/main.py`가 띄우는 FastAPI 서버(예: `localhost:8000`)로 요청을 보냅니다.
2.  **`script_gen/state.py` 성역화**: 태윤님과 빛나님은 이 파일의 변수명(`news_data`, `youtube_data`, `draft_script`)을 먼저 합의하고 개발을 시작합니다.
3.  **DB 스키마**: 도헌님이 `shared/database.py`에 정의한 모델을 전 팀원이 import해서 사용합니다.

