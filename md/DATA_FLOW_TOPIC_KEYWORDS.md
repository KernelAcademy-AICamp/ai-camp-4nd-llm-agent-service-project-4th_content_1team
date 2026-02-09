# 🔍 토픽 & 검색 키워드 데이터 흐름 (상세 코드 리뷰)

**작성일**: 2026-02-09  
**목적**: 스크립트 생성 시 `topic`과 `search_keywords`가 어디서 만들어지고, 어떤 경로를 거쳐서 뉴스 검색까지 도달하는지 **실제 코드 기반으로** 추적

---

## 📌 전체 흐름 요약도

```
[STEP 0] DB에 search_keywords가 미리 저장되어 있음
         └── channel_topics 테이블
         └── trend_topics 테이블
              ↓
[STEP 1] FE: 사용자가 추천 주제 선택 → topic + topicId를 URL에 담음
              ↓
[STEP 2] FE: executeScriptGen(topic, topicId) → API 호출
              ↓
[STEP 3] BE API: /script-gen/execute → build_planner_input() 호출
              ↓
[STEP 4] BE input_builder: DB에서 channel_topics/trend_topics 조회 → search_keywords 포함한 topic_context 생성
              ↓
[STEP 5] BE API: topic_context를 channel_profile에 병합 → Celery Task에 전달
              ↓
[STEP 6] Celery Worker: generate_script() 호출
              ↓
[STEP 7] news_research_node: channel_profile → topic_context → search_keywords 꺼내서 네이버 검색
              ↓
[STEP 8] planner_node: channel_profile → topic_context → search_keywords를 프롬프트에 포함
```

---

## STEP 0: DB에 search_keywords가 저장되는 과정

### 저장 위치: `channel_topics` / `trend_topics` 테이블

Adminer에서 확인한 것처럼, 두 테이블 모두 `search_keywords` 컬럼(JSONB)이 있음.

### 누가 저장하나?

`BE/src/topic_rec/nodes/recommender.py` (주제 추천 노드)가 GPT에게 요청해서 생성 후 저장.

```python
# BE/src/topic_rec/nodes/recommender.py (154줄, 179줄)

# GPT에게 보내는 프롬프트에 search_keywords를 요청함
"""
- search_keywords: 스크립트 자료조사용 검색 키워드 (3~5개, 배열)
"""

# GPT 응답 예시:
[{
    "title": "챗GPT와 클로드 비교 분석",
    "search_keywords": ["챗GPT 클로드 비교", "ChatGPT vs Claude", "OpenAI Anthropic"],
    ...
}]
```

```python
# BE/src/topic_rec/nodes/recommender.py (215~235줄)

# GPT 응답에서 search_keywords를 파싱
raw_keywords = item.get("search_keywords", [])

if isinstance(raw_keywords, list):
    search_keywords = raw_keywords      # 배열이면 그대로 사용
elif isinstance(raw_keywords, dict):
    search_keywords = []
    for key in raw_keywords:
        search_keywords.extend(raw_keywords.get(key, []))
    search_keywords = list(set(search_keywords))[:5]  # 중복 제거 후 최대 5개
else:
    search_keywords = []

# 최종 결과에 포함
{
    "title": ...,
    "search_keywords": search_keywords,  # ← 여기!
    ...
}
```

### DB에 저장하는 코드

`BE/app/services/recommendation_service.py`에서 위 결과를 받아서 DB에 저장:

```python
# BE/app/services/recommendation_service.py (160줄, 222줄)

# ChannelTopic 또는 TrendTopic 모델에 저장
search_keywords=rec.get("search_keywords", []),
```

### DB 모델

```python
# BE/app/models/content_topic.py (81줄, 195줄)

class ChannelTopic(Base):
    search_keywords = Column(JSONB, default=list)  # ["키워드1", "키워드2", ...]

class TrendTopic(Base):
    search_keywords = Column(JSONB, default=list)  # ["키워드1", "키워드2", ...]
```

### 핵심 포인트
- `search_keywords`는 **스크립트 생성 파이프라인과 완전히 별개의 시점**에 만들어짐
- 사용자가 대시보드에서 주제를 확인하기 **전**에 이미 DB에 저장되어 있음
- recommender가 주제를 추천하면서 "이 주제로 뉴스 검색할 때 쓸 키워드"를 미리 만들어 두는 구조

---

## STEP 1: FE - 사용자가 주제 선택

### 파일: `FE/src/pages/script/page.tsx`

사용자가 대시보드에서 추천 주제를 클릭하면, URL 파라미터로 `topic`과 `topicId`가 전달됨.

```tsx
// FE/src/pages/script/page.tsx (14~16줄)

function ScriptPageContent() {
  const [searchParams] = useSearchParams()
  const topic = searchParams.get("topic") || "2026 게임 트렌드 예측"
  const topicId = searchParams.get("topicId") || undefined
  // topic = "챗GPT와 클로드(Claude) 비교 분석"
  // topicId = "a1b2c3d4-..." (channel_topics 또는 trend_topics 테이블의 id)
```

### URL 예시
```
/script?topic=챗GPT와+클로드(Claude)+비교+분석&topicId=a1b2c3d4-e5f6-7890-abcd-1234567890ab
```

---

## STEP 2: FE - API 호출

### 파일: `FE/src/pages/script/page.tsx`

"생성" 버튼 클릭 시 `executeScriptGen` 호출:

```tsx
// FE/src/pages/script/page.tsx (44~48줄)

const handleGenerate = async () => {
  setIsGenerating(true)
  try {
    const { task_id } = await executeScriptGen(topic, topicId)
    //                                         ↑       ↑
    //                               "챗GPT와..."   "a1b2c3d4-..."
```

### 파일: `FE/src/lib/api/services/script-gen.service.ts`

실제 API 호출 코드:

```typescript
// FE/src/lib/api/services/script-gen.service.ts (48~54줄)

export const executeScriptGen = async (
  topic: string,
  topicRecommendationId?: string
): Promise<TaskStatusResponse> => {
    const response = await api.post('/script-gen/execute', {
        topic,                                        // "챗GPT와 클로드(Claude) 비교 분석"
        topic_recommendation_id: topicRecommendationId, // "a1b2c3d4-..." (channel_topics.id)
    });
    return response.data;
};
```

### 실제 HTTP 요청
```json
POST /api/v1/script-gen/execute
{
  "topic": "챗GPT와 클로드(Claude) 비교 분석",
  "topic_recommendation_id": "a1b2c3d4-e5f6-7890-abcd-1234567890ab"
}
```

---

## STEP 3: BE API - 요청 수신 & input 빌드

### 파일: `BE/app/api/routes/script_gen.py`

```python
# BE/app/api/routes/script_gen.py (52~89줄)

@router.post("/execute", response_model=ScriptGenTaskResponse)
async def execute_pipeline_async(
    request: ScriptGenStartRequest,   # ← Pydantic이 JSON을 파싱
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. build_planner_input 호출 (여기서 DB 조회!)
    planner_input = await build_planner_input(
        db=db,
        topic=request.topic,                           # "챗GPT와 클로드(Claude) 비교 분석"
        user_id=str(current_user.id),                  # 현재 로그인한 유저
        topic_recommendation_id=request.topic_recommendation_id,  # "a1b2c3d4-..."
    )
```

### Pydantic 스키마 (요청 파싱용)

```python
# BE/app/schemas/script_gen.py (14~27줄)

class ScriptGenStartRequest(BaseModel):
    topic: str = Field(..., description="영상 주제")
    topic_recommendation_id: Optional[str] = Field(None, description="AI 추천 주제 ID")
```

---

## STEP 4: input_builder - DB에서 search_keywords 조회

### 파일: `BE/src/script_gen/utils/input_builder.py`

이 파일이 **핵심**. DB에서 데이터를 꺼내서 파이프라인 입력을 만듦.

### 4-1. 전체 흐름

```python
# BE/src/script_gen/utils/input_builder.py (24~103줄)

async def build_planner_input(db, topic, user_id, topic_recommendation_id=None):

    # ========== 1. 채널 정보 조회 ==========
    channel = await _get_user_channel(db, user_id)
    # → youtube_channels 테이블에서 유저의 채널 조회

    # ========== 2. 페르소나 조회 ==========
    persona = await _get_channel_persona(db, channel.channel_id)
    # → channel_personas 테이블에서 채널의 페르소나 조회

    # ========== 3. channel_profile 구성 ==========
    channel_profile = _build_channel_profile(channel, persona)
    # → 채널명, 카테고리, 타겟 오디언스, 스타일 등

    # ========== 4. topic_context 구성 (★ search_keywords가 여기서 나옴!) ==========
    topic_context = None
    if topic_recommendation_id:   # ← topicId가 있을 때만!
        topic_context = await _build_topic_context(
            db, channel.channel_id, topic_recommendation_id
        )

    # ========== 5. 최종 반환 ==========
    return {
        "topic": topic,                    # "챗GPT와 클로드(Claude) 비교 분석"
        "channel_profile": channel_profile, # 채널 정보 dict
        "topic_context": topic_context,     # search_keywords 포함 dict (또는 None)
    }
```

### 4-2. _build_topic_context (★ search_keywords 조회)

```python
# BE/src/script_gen/utils/input_builder.py (199~254줄)

async def _build_topic_context(db, channel_id, topic_recommendation_id):

    # 1차: channel_topics 테이블에서 조회
    result = await db.execute(
        select(ChannelTopic).where(
            ChannelTopic.id == topic_recommendation_id  # "a1b2c3d4-..."
        )
    )
    topic = result.scalar_one_or_none()

    # 2차: channel_topics에 없으면 trend_topics에서 조회
    if not topic:
        result = await db.execute(
            select(TrendTopic).where(
                TrendTopic.id == topic_recommendation_id
            )
        )
        topic = result.scalar_one_or_none()

    if not topic:
        return None  # 못 찾으면 None

    # topic_context dict 생성
    context = {
        "source": "ai_recommendation",
        "trend_basis": topic.trend_basis or "",
        "urgency": topic.urgency or "normal",
        "content_angles": topic.content_angles or [],
        "recommendation_reason": topic.recommendation_reason or "",
        "search_keywords": topic.search_keywords or [],   # ★★★ 여기!!! ★★★
        "based_on_topic": topic.based_on_topic or "",
    }
    # 예시 결과:
    # {
    #     "source": "ai_recommendation",
    #     "search_keywords": ["챗GPT 클로드 비교", "ChatGPT vs Claude", "OpenAI Anthropic"],
    #     ...
    # }

    return context
```

### 핵심 포인트
- `topic_recommendation_id`가 **None이면 topic_context 자체가 None** → search_keywords도 없음
- `topic_recommendation_id`가 있어야 DB에서 `search_keywords`를 꺼내올 수 있음
- 이것이 **어제 수정한 버그의 원인**: FE에서 `topicId`를 안 보내면 → `topic_recommendation_id`가 None → search_keywords가 빈 배열

---

## STEP 5: BE API - topic_context를 channel_profile에 병합

### 파일: `BE/app/api/routes/script_gen.py`

```python
# BE/app/api/routes/script_gen.py (75~89줄)

    # topic_context를 channel_profile 안에 넣음!
    channel_profile = planner_input["channel_profile"].copy()
    if planner_input.get("topic_context"):
        channel_profile["topic_context"] = planner_input["topic_context"]
        # channel_profile = {
        #     "name": "채널명",
        #     "category": "tech",
        #     "topic_context": {                              ← 여기에 끼워넣음!
        #         "search_keywords": ["챗GPT 클로드 비교", ...],
        #         "trend_basis": "...",
        #         ...
        #     }
        # }

    # Celery Task에 전달
    task = task_generate_script.delay(
        topic=planner_input["topic"],        # "챗GPT와 클로드(Claude) 비교 분석"
        channel_profile=channel_profile,     # search_keywords가 들어있는 dict
        topic_request_id=None,
        user_id=str(current_user.id),
        channel_id=channel_profile.get("channel_id"),
    )
```

### 이 시점의 channel_profile 구조
```python
{
    "name": "테크 리뷰 채널",
    "category": "tech",
    "target_audience": "IT 종사자",
    "content_style": "분석형",
    "main_topics": ["AI", "개발"],
    "topic_context": {                    # ★ 여기에 search_keywords가 들어있음
        "source": "ai_recommendation",
        "trend_basis": "최근 AI 모델 경쟁 심화",
        "urgency": "urgent",
        "content_angles": ["성능 비교", "가격 비교"],
        "recommendation_reason": "채널 주제와 부합",
        "search_keywords": [              # ★★★ 이게 최종적으로 뉴스 검색에 사용됨
            "챗GPT 클로드 비교",
            "ChatGPT vs Claude",
            "OpenAI Anthropic"
        ],
        "based_on_topic": "AI 모델 경쟁"
    }
}
```

---

## STEP 6: Celery Worker → generate_script 호출

### 파일: `BE/app/worker.py`

```python
# BE/app/worker.py (85~110줄)

@celery_app.task(bind=True)
def task_generate_script(self, topic, channel_profile, topic_request_id=None, user_id=None, channel_id=None):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # TopicRequest 생성 (DB 이력용)
    if not topic_request_id:
        topic_request_id = loop.run_until_complete(
            _create_topic_request(topic, user_id, channel_id)
        )

    # ★ 파이프라인 실행 (channel_profile에 search_keywords가 들어있는 상태로 전달)
    result = loop.run_until_complete(generate_script(
        topic=topic,                  # "챗GPT와 클로드(Claude) 비교 분석"
        channel_profile=channel_profile,  # search_keywords 포함
        topic_request_id=topic_request_id
    ))
```

---

## STEP 7: news_research_node - search_keywords 꺼내서 뉴스 검색

### 파일: `BE/src/script_gen/nodes/news_research.py`

```python
# BE/src/script_gen/nodes/news_research.py (37~59줄)

def news_research_node(state):
    # 1. channel_profile에서 topic_context를 꺼냄
    channel_profile = state.get("channel_profile", {})
    topic_context = channel_profile.get("topic_context", {})

    # 2. topic_context에서 search_keywords를 꺼냄
    base_queries = topic_context.get("search_keywords", []) if topic_context else []
    # base_queries = ["챗GPT 클로드 비교", "ChatGPT vs Claude", "OpenAI Anthropic"]

    if not base_queries:
        return {"news_data": {"articles": []}}  # ← 키워드 없으면 빈 결과!

    # 3. 네이버 뉴스 검색 (키워드별 15개씩)
    raw_articles = _fetch_naver_news_bulk(base_queries)
    # → "챗GPT 클로드 비교"로 15개, "ChatGPT vs Claude"로 15개, ... 총 45개 후보

    # 4. GPT로 관련 기사 필터링 (Chain-of-Thought)
    relevant_articles = _filter_relevant_articles(raw_articles, topic, search_keywords=base_queries)

    # 5. 중복 제거 → 최종 5개 선별
    unique_articles = _deduplicate_articles(relevant_articles)

    # 6. 본문 크롤링 & AI 분석
    full_articles = _crawl_and_analyze(unique_articles)
```

### GPT 필터 프롬프트 (Chain-of-Thought)

```python
# BE/src/script_gen/nodes/news_research.py (126~168줄)

prompt = f"""당신은 YouTube 스크립트 작성을 위한 뉴스 기사 선별 전문가입니다.

[영상 주제]
"{topic}"

[검색 키워드]
{keywords_str}

[판단 프로세스 - 반드시 이 순서대로 수행]

Step 1. 핵심 대상 추출
영상 주제에서 핵심 대상(고유명사: 제품명, 인물명, 기업명, 기술명)을 추출하세요.
"AI", "기술" 같은 범용 단어는 핵심 대상이 아닙니다.

Step 2. 기사별 판단
"영상 스크립트를 쓰는 사람이 이 기사를 열었을 때, 스크립트에 직접 인용할 내용을 찾을 수 있는가?"

포함 (O):
- 기사의 주제 자체가 핵심 대상에 관한 것
- 핵심 대상의 성능, 기능, 비교를 직접 다루는 기사

제외 (X):
- 핵심 대상이 제목과 설명에 전혀 등장하지 않는 기사
- 다른 분야 기사에서 핵심 대상을 잠깐 언급하는 기사
"""
```

---

## STEP 8: planner_node - search_keywords를 프롬프트에 포함

### 파일: `BE/src/script_gen/nodes/planner.py`

Planner도 `search_keywords`를 사용함. 뉴스 검색 쿼리(newsQuery) 생성 시 참고하도록 프롬프트에 넣음.

```python
# BE/src/script_gen/nodes/planner.py (236~240줄)

    # channel_topics/trend_topics에서 가져온 검색 키워드 (newsQuery 생성 시 참고)
    if topic_context_data.get('search_keywords'):
        topic_context += "- Pre-researched Keywords (USE these as base for newsQuery):\n"
        for kw in topic_context_data.get('search_keywords', []):
            topic_context += f"  • {kw}\n"

    # 이 결과가 Planner GPT 프롬프트에 포함됨:
    # "- Pre-researched Keywords (USE these as base for newsQuery):
    #   • 챗GPT 클로드 비교
    #   • ChatGPT vs Claude
    #   • OpenAI Anthropic"
```

---

## 🗺️ 데이터 흐름 한눈에 보기 (파일 + 코드 라인)

```
┌─────────────────────────────────────────────────────────────────────┐
│ [STEP 0] DB에 이미 저장됨                                            │
│                                                                     │
│ recommender.py (154줄)                                              │
│   └── GPT에게 search_keywords 요청                                  │
│   └── recommendation_service.py (160줄) → DB 저장                   │
│   └── content_topic.py (81줄) → channel_topics.search_keywords      │
│   └── content_topic.py (195줄) → trend_topics.search_keywords       │
└────────────────────────┬────────────────────────────────────────────┘
                         │ DB (JSONB 컬럼)
                         ↓
┌─────────────────────────────────────────────────────────────────────┐
│ [STEP 1~2] 프론트엔드                                                │
│                                                                     │
│ page.tsx (14~16줄)                                                  │
│   └── URL에서 topic, topicId 파싱                                    │
│                                                                     │
│ script-gen.service.ts (48~54줄)                                     │
│   └── POST /script-gen/execute                                      │
│   └── body: { topic, topic_recommendation_id: topicId }             │
└────────────────────────┬────────────────────────────────────────────┘
                         │ HTTP POST
                         ↓
┌─────────────────────────────────────────────────────────────────────┐
│ [STEP 3~5] 백엔드 API                                               │
│                                                                     │
│ script_gen.py (52~89줄)     ← API 엔드포인트                         │
│   └── build_planner_input() 호출                                     │
│                                                                     │
│ input_builder.py (24~103줄) ← 핵심 빌더                              │
│   ├── _get_user_channel()   → youtube_channels 테이블 조회           │
│   ├── _get_channel_persona()→ channel_personas 테이블 조회           │
│   ├── _build_channel_profile()                                      │
│   └── _build_topic_context() (199~254줄) ★★★                       │
│       └── channel_topics 또는 trend_topics에서 id로 조회              │
│       └── topic.search_keywords → context["search_keywords"]        │
│                                                                     │
│ script_gen.py (75~89줄)                                              │
│   └── channel_profile["topic_context"] = topic_context ← 병합!      │
│   └── task_generate_script.delay(channel_profile=...)                │
└────────────────────────┬────────────────────────────────────────────┘
                         │ Celery Queue (Redis)
                         ↓
┌─────────────────────────────────────────────────────────────────────┐
│ [STEP 6] Celery Worker                                              │
│                                                                     │
│ worker.py (85~110줄)                                                │
│   └── generate_script(topic, channel_profile) 호출                   │
└────────────────────────┬────────────────────────────────────────────┘
                         │ LangGraph State
                         ↓
┌─────────────────────────────────────────────────────────────────────┐
│ [STEP 7] News Research Node                                         │
│                                                                     │
│ news_research.py (37~59줄)                                          │
│   └── state["channel_profile"]["topic_context"]["search_keywords"]  │
│   └── base_queries = ["챗GPT 클로드 비교", "ChatGPT vs Claude", ...]  │
│   └── _fetch_naver_news_bulk(base_queries)  → 네이버 검색             │
│   └── _filter_relevant_articles()            → GPT 필터              │
│   └── _deduplicate_articles()                → 중복 제거              │
│   └── _crawl_and_analyze()                   → 본문 크롤링            │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ [STEP 8] Planner Node                                               │
│                                                                     │
│ planner.py (236~240줄)                                              │
│   └── search_keywords를 GPT 프롬프트에 포함                          │
│   └── "Pre-researched Keywords (USE these as base for newsQuery)"   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ⚠️ 발견된 문제점 & 어제 수정한 버그

### 버그: FE에서 topicId 미전달

**원인**: 대시보드에서 스크립트 페이지로 이동할 때 URL에 `topicId`를 안 넣었음

```
수정 전: /script?topic=챗GPT와+클로드+비교
수정 후: /script?topic=챗GPT와+클로드+비교&topicId=a1b2c3d4-...
```

**결과**: `topic_recommendation_id`가 None → `_build_topic_context()` 실행 안 됨 → `search_keywords`가 빈 배열 → 뉴스 검색 결과 0개

### 데이터가 경유하는 파일 목록 (총 6개)

| 순서 | 파일 | 역할 |
|:---:|:---|:---|
| 1 | `FE/src/pages/script/page.tsx` | URL에서 topicId 파싱 |
| 2 | `FE/src/lib/api/services/script-gen.service.ts` | API 요청에 topic_recommendation_id 포함 |
| 3 | `BE/app/api/routes/script_gen.py` | build_planner_input 호출 + topic_context 병합 |
| 4 | `BE/src/script_gen/utils/input_builder.py` | DB 조회 → search_keywords 포함한 topic_context 생성 |
| 5 | `BE/src/script_gen/nodes/news_research.py` | search_keywords로 네이버 뉴스 검색 |
| 6 | `BE/src/script_gen/nodes/planner.py` | search_keywords를 GPT 프롬프트에 포함 |

### 관련 DB 테이블

| 테이블 | 컬럼 | 용도 |
|:---|:---|:---|
| `channel_topics` | `search_keywords` (JSONB) | 채널 맞춤 추천 주제의 검색 키워드 |
| `trend_topics` | `search_keywords` (JSONB) | 트렌드 기반 추천 주제의 검색 키워드 |

---

## 📝 Pydantic 스키마

### 요청 (FE → BE)
```python
# BE/app/schemas/script_gen.py
class ScriptGenStartRequest(BaseModel):
    topic: str                                    # "챗GPT와 클로드 비교 분석"
    topic_recommendation_id: Optional[str] = None # "a1b2c3d4-..." (channel_topics.id)
```

### 응답 (디버깅용)
```python
class TopicContextResponse(BaseModel):
    source: str
    trend_basis: str
    urgency: str
    content_angles: List[str]
    recommendation_reason: str
    search_keywords: List[str] = Field(default_factory=list)
    # ↑ default_factory=list:
    #   값이 없으면 빈 리스트 [] 로 처리 (에러 방지)
```
