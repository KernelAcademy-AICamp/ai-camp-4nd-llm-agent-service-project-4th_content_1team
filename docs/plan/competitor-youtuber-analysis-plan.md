# 경쟁 유튜버 분석 에이전트 계획서

## 📋 목차
1. [개요](#개요)
2. [경쟁 유튜버 선정 기준](#경쟁-유튜버-선정-기준)
3. [기술 구현 방법](#기술-구현-방법)
4. [시스템 아키텍처](#시스템-아키텍처)
5. [구현 단계](#구현-단계)
6. [예상 결과](#예상-결과)

---

## 개요

### 🎯 목표
내 채널과 경쟁 관계에 있는 유튜버들을 자동으로 발견하고 분석하여, 벤치마킹 및 차별화 전략 수립에 활용

### 💡 핵심 가치
- **자동화**: 수동 검색 없이 AI가 경쟁자 자동 발견
- **정확성**: 카테고리, 타겟층, 규모를 종합 고려
- **실시간**: 급성장 채널 즉시 포착

---

## 경쟁 유튜버 선정 기준

### 1️⃣ 카테고리 일치
**기준**: 같은 주제/분야를 다루는 채널

**YouTube API 활용**:
```python
# YouTube Data API - channels.list
GET /channels
params:
  - part: "topicDetails"
  - id: channel_id

response:
  topicDetails:
    topicCategories: [
      "https://en.wikipedia.org/wiki/Technology",
      "https://en.wikipedia.org/wiki/Education"
    ]
```

**AI 보완**:
- 채널 설명, 영상 제목 분석
- 내 채널 페르소나의 `main_topics`와 비교
- 유사도 점수 계산 (임베딩 기반)

### 2️⃣ 시청자 타겟층 유사
**기준**: 시청자 연령대, 관심사가 유사한 채널

**YouTube Analytics API** (제한적):
```python
# 내 채널만 접근 가능
GET /reports
params:
  - dimensions: "ageGroup,gender"
  - metrics: "viewerPercentage"
```

**AI 추론**:
```python
# 경쟁 채널의 타겟층 추론
분석 요소:
  1. 채널 설명 톤앤매너
  2. 영상 제목 스타일
  3. 댓글 분석 (언어 패턴, 관심사)
  4. 썸네일 스타일

LLM 프롬프트:
"이 채널의 주요 시청자층은 누구인가?
- 연령대 (10대/20대/30대/전연령)
- 직업군 (학생/직장인/전문가)
- 관심사"
```

### 3️⃣ 규모 기준
**기준**: 
- 유사 규모: 내 채널 구독자 ±50% 범위
- 더 큰 규모: 내 채널의 1.5배 ~ 10배
- 급성장: 최근 30일 조회수 증가율 +50% 이상

**YouTube API**:
```python
# channels.list로 통계 조회
statistics:
  subscriberCount: 100000
  viewCount: 5000000
  videoCount: 150

# 성장률 계산 (최근 영상 vs 과거 영상 비교)
recent_videos = videos uploaded in last 30 days
avg_views_recent = mean(recent_videos.viewCount)
avg_views_old = mean(older_videos.viewCount)
growth_rate = (avg_views_recent - avg_views_old) / avg_views_old
```

---

## 기술 구현 방법

### Step 1: 내 채널 페르소나 기반 검색 쿼리 생성

```python
my_persona = {
  "main_topics": ["AI 코딩", "웹개발", "개발자 교육"],
  "target_audience": "20대 중반~30대 초반 개발자",
  "analyzed_categories": ["교육", "기술", "개발"],
  "subscriber_count": 118000,
  "content_style": "실전 코딩 튜토리얼"
}

# AI로 검색 쿼리 생성
llm_prompt = f"""
내 채널 정보:
- 주제: {my_persona['main_topics']}
- 타겟: {my_persona['target_audience']}
- 카테고리: {my_persona['analyzed_categories']}

경쟁 채널을 찾기 위한 YouTube 검색어 3~5개 생성:
(예: "AI 코딩 튜토리얼", "웹개발 강의", "개발자 교육")
"""

search_queries = llm.invoke(llm_prompt)
→ ["AI 코딩 튜토리얼", "프로그래밍 교육", "웹개발 입문"]
```

### Step 2: YouTube API로 채널 검색

```python
# search.list API로 채널 검색
for query in search_queries:
    response = youtube.search().list(
        part="snippet",
        q=query,
        type="channel",
        maxResults=20,
        order="viewCount"  # 조회수 순
    ).execute()
    
    candidate_channels.extend(response['items'])
```

### Step 3: 채널 상세 정보 조회

```python
# channels.list API로 통계 및 세부 정보
channel_ids = [ch['id']['channelId'] for ch in candidate_channels]

details = youtube.channels().list(
    part="snippet,statistics,topicDetails,brandingSettings",
    id=",".join(channel_ids)
).execute()

for channel in details['items']:
    channel_info = {
        "id": channel['id'],
        "title": channel['snippet']['title'],
        "description": channel['snippet']['description'],
        "subscriber_count": int(channel['statistics']['subscriberCount']),
        "view_count": int(channel['statistics']['viewCount']),
        "video_count": int(channel['statistics']['videoCount']),
        "topic_categories": channel.get('topicDetails', {}).get('topicCategories', []),
        "keywords": channel.get('brandingSettings', {}).get('channel', {}).get('keywords', "")
    }
```

### Step 4: AI로 유사도 분석

```python
# 각 경쟁 채널과 내 채널의 유사도 계산
for competitor in competitor_channels:
    similarity_prompt = f"""
    내 채널:
    - 주제: {my_persona['main_topics']}
    - 타겟: {my_persona['target_audience']}
    - 스타일: {my_persona['content_style']}
    
    경쟁 채널:
    - 제목: {competitor['title']}
    - 설명: {competitor['description']}
    - 키워드: {competitor['keywords']}
    
    0~100 점수로 유사도 평가:
    - 카테고리 일치도 (0~30점)
    - 타겟층 일치도 (0~40점)
    - 콘텐츠 스타일 일치도 (0~30점)
    
    JSON으로 반환: {{"score": 75, "reason": "..."}}
    """
    
    result = llm.invoke(similarity_prompt)
    competitor['similarity_score'] = result['score']
```

### Step 5: 규모 및 성장률 필터링

```python
# 1. 규모 기준 필터링
my_subscribers = 118000
filtered = []

for ch in competitor_channels:
    sub_count = ch['subscriber_count']
    
    # 유사 규모 (±50%)
    if my_subscribers * 0.5 <= sub_count <= my_subscribers * 1.5:
        ch['tier'] = 'similar'
        filtered.append(ch)
    
    # 더 큰 규모 (1.5배 ~ 10배)
    elif my_subscribers * 1.5 < sub_count <= my_subscribers * 10:
        ch['tier'] = 'larger'
        filtered.append(ch)

# 2. 급성장 채널 추가
growth_candidates = await analyze_channel_growth(competitor_channels)
for ch in growth_candidates:
    if ch['growth_rate'] > 0.5:  # 50% 이상 성장
        ch['tier'] = 'rising_star'
        filtered.append(ch)
```

### Step 6: 최종 우선순위 정렬

```python
# 종합 점수 계산
for ch in filtered:
    engagement_rate = ch.get('avg_likes', 0) / max(ch.get('avg_views', 1), 1)
    
    final_score = (
        ch['similarity_score'] * 0.4 +      # 유사도 40%
        min(ch['subscriber_count'] / 10000, 100) * 0.3 +  # 규모 30%
        ch.get('growth_rate', 0) * 100 * 0.2 +  # 성장률 20%
        engagement_rate * 1000 * 0.1  # 참여도 10%
    )
    
    ch['final_score'] = final_score

# 점수 순 정렬
sorted_competitors = sorted(filtered, key=lambda x: x['final_score'], reverse=True)
return sorted_competitors[:20]  # 상위 20개
```

---

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│             경쟁 유튜버 분석 에이전트                      │
└─────────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Step 1    │ │   Step 2    │ │   Step 3    │
│ 페르소나    │ │ YouTube     │ │ 채널 상세   │
│ 기반 쿼리   │ │ 채널 검색   │ │ 정보 수집   │
└─────────────┘ └─────────────┘ └─────────────┘
        │               │               │
        └───────────────┼───────────────┘
                        ▼
                ┌─────────────┐
                │   Step 4    │
                │ AI 유사도   │
                │   분석      │
                └─────────────┘
                        │
                        ▼
                ┌─────────────┐
                │   Step 5    │
                │ 규모/성장률 │
                │  필터링     │
                └─────────────┘
                        │
                        ▼
                ┌─────────────┐
                │   Step 6    │
                │ 우선순위    │
                │   정렬      │
                └─────────────┘
                        │
                        ▼
                ┌─────────────┐
                │    결과     │
                │ Top 20 경쟁 │
                │   채널      │
                └─────────────┘
```

---

## 구현 단계

### Phase 1: 기초 인프라 (1-2일)

**1.1 DB 스키마 설계**
```sql
CREATE TABLE competitor_channels (
    id UUID PRIMARY KEY,
    channel_id VARCHAR NOT NULL,
    title VARCHAR,
    description TEXT,
    subscriber_count INTEGER,
    view_count BIGINT,
    video_count INTEGER,
    topic_categories JSONB,  -- YouTube topicDetails
    
    -- AI 분석 결과
    similarity_score FLOAT,  -- 0~100
    similarity_reason TEXT,
    target_audience TEXT,
    content_style TEXT,
    
    -- 규모/성장 정보
    tier VARCHAR,  -- 'similar', 'larger', 'rising_star'
    growth_rate FLOAT,
    avg_views_recent INTEGER,
    
    -- 메타
    analyzed_at TIMESTAMP,
    last_updated TIMESTAMP,
    
    -- 관계
    reference_channel_id VARCHAR,  -- 내 채널 ID
    FOREIGN KEY (reference_channel_id) REFERENCES youtube_channels(channel_id)
);
```

**1.2 서비스 계층**
```python
# app/services/competitor_channel_service.py
class CompetitorChannelService:
    @staticmethod
    async def find_competitors(
        my_channel_id: str,
        db: AsyncSession
    ) -> List[CompetitorChannel]:
        """경쟁 채널 발견 및 분석"""
        pass
```

---

### Phase 2: 검색 쿼리 생성 (AI)

**2.1 페르소나 기반 검색어 추출**
```python
async def generate_search_queries(persona: ChannelPersona) -> List[str]:
    """
    내 채널 페르소나로부터 검색어 생성
    
    Input:
        persona.main_topics: ["AI 코딩", "웹개발"]
        persona.content_style: "실전 튜토리얼"
        persona.target_audience: "20대 개발자"
    
    Output:
        ["AI 코딩 튜토리얼", "웹개발 강의", "프로그래밍 입문"]
    """
    prompt = f"""
    채널 정보:
    - 주제: {persona.main_topics}
    - 스타일: {persona.content_style}
    - 타겟: {persona.target_audience}
    
    위 채널과 유사한 채널을 찾기 위한 YouTube 검색어 5개 생성.
    검색어는 구체적이고 명확해야 함.
    
    JSON: {{"queries": ["검색어1", "검색어2", ...]}}
    """
    
    result = openai_llm.invoke(prompt)
    return result['queries']
```

---

### Phase 3: YouTube API 채널 검색

**3.1 채널 검색**
```python
async def search_channels_by_query(
    query: str,
    max_results: int = 20
) -> List[str]:
    """
    YouTube search.list API로 채널 검색
    
    Returns:
        채널 ID 리스트
    """
    params = {
        "part": "snippet",
        "q": query,
        "type": "channel",
        "maxResults": max_results,
        "order": "viewCount",  # 조회수 순
        "key": YOUTUBE_API_KEY
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/youtube/v3/search",
            params=params
        )
        data = resp.json()
        
        return [
            item['id']['channelId']
            for item in data.get('items', [])
            if item.get('id', {}).get('channelId')
        ]
```

**3.2 채널 상세 정보 조회**
```python
async def get_channel_details(
    channel_ids: List[str]
) -> List[Dict]:
    """
    channels.list API로 채널 상세 정보 조회
    """
    params = {
        "part": "snippet,statistics,topicDetails,brandingSettings",
        "id": ",".join(channel_ids),
        "key": YOUTUBE_API_KEY
    }
    
    # ... (구현)
    return channel_details
```

---

### Phase 4: AI 유사도 분석

**4.1 채널 간 유사도 계산**
```python
async def calculate_similarity(
    my_persona: ChannelPersona,
    competitor_channel: Dict
) -> Dict[str, Any]:
    """
    LLM으로 채널 간 유사도 분석
    """
    prompt = f"""
    **내 채널 (기준)**:
    - 주제: {my_persona.main_topics}
    - 타겟: {my_persona.target_audience}
    - 스타일: {my_persona.content_style}
    - 차별화: {my_persona.differentiator}
    
    **경쟁 후보 채널**:
    - 제목: {competitor_channel['title']}
    - 설명: {competitor_channel['description'][:500]}
    - 키워드: {competitor_channel.get('keywords', '')}
    - 카테고리: {competitor_channel.get('topic_categories', [])}
    
    ---
    
    다음 기준으로 0~100점 평가:
    
    1. **카테고리 일치도** (0~30점)
       - 주제가 얼마나 겹치는가?
    
    2. **타겟층 일치도** (0~40점)
       - 시청자층이 얼마나 유사한가?
    
    3. **콘텐츠 스타일 일치도** (0~30점)
       - 영상 스타일이 얼마나 비슷한가?
    
    **출력 JSON**:
    {{
        "total_score": 75,
        "category_score": 25,
        "audience_score": 35,
        "style_score": 15,
        "reason": "둘 다 AI 코딩 교육을 다루며, 20대 개발자를 타겟으로 함. 
                   하지만 경쟁 채널은 이론 중심, 내 채널은 실전 중심으로 스타일 차이 있음.",
        "target_audience_inferred": "20대 초반 ~ 30대 초반 개발자",
        "is_competitor": true  // 60점 이상이면 true
    }}
    """
    
    result = llm.invoke(prompt)
    return result
```

**4.2 임베딩 기반 유사도 (보조)**
```python
# 채널 설명 임베딩
from langchain.embeddings import OpenAIEmbeddings

embeddings = OpenAIEmbeddings()

my_embedding = embeddings.embed_query(my_persona.persona_summary)
competitor_embedding = embeddings.embed_query(competitor_channel['description'])

# 코사인 유사도
from numpy import dot
from numpy.linalg import norm

cosine_sim = dot(my_embedding, competitor_embedding) / (norm(my_embedding) * norm(competitor_embedding))
```

---

### Phase 5: 성장률 분석

**5.1 최근 영상 성과 분석**
```python
async def analyze_channel_growth(channel_id: str) -> float:
    """
    채널의 최근 30일 vs 과거 성장률 계산
    """
    # 1. 채널의 최근 영상 20개 조회
    recent_videos = await get_channel_videos(
        channel_id,
        max_results=20,
        order="date"
    )
    
    # 2. 30일 기준으로 분리
    now = datetime.now()
    recent = [v for v in recent_videos if (now - v['published_at']).days <= 30]
    old = [v for v in recent_videos if (now - v['published_at']).days > 30]
    
    if not recent or not old:
        return 0.0
    
    # 3. 평균 조회수 비교
    avg_views_recent = sum(v['view_count'] for v in recent) / len(recent)
    avg_views_old = sum(v['view_count'] for v in old) / len(old)
    
    growth_rate = (avg_views_recent - avg_views_old) / max(avg_views_old, 1)
    
    return growth_rate
```

---

### Phase 6: 최종 필터링 및 정렬

**6.1 규모 기준 분류**
```python
def classify_by_size(
    competitor: Dict,
    my_subscribers: int
) -> str:
    """규모 기준 tier 분류"""
    ratio = competitor['subscriber_count'] / my_subscribers
    
    if 0.5 <= ratio <= 1.5:
        return 'similar'  # 유사 규모
    elif 1.5 < ratio <= 10:
        return 'larger'   # 벤치마킹 대상
    elif ratio > 10:
        return 'giant'    # 거대 채널 (참고용)
    else:
        return 'smaller'  # 작은 채널 (제외)
```

**6.2 종합 점수 계산**
```python
def calculate_final_score(competitor: Dict) -> float:
    """
    종합 점수 = 유사도 40% + 규모 30% + 성장률 20% + 참여도 10%
    """
    similarity = competitor.get('similarity_score', 0)  # 0~100
    size_score = min(competitor['subscriber_count'] / 10000, 100)  # 정규화
    growth_score = min(competitor.get('growth_rate', 0) * 100, 100)  # 0.5 → 50점
    engagement = (competitor.get('avg_likes', 0) / max(competitor.get('avg_views', 1), 1)) * 1000
    
    final = (
        similarity * 0.4 +
        size_score * 0.3 +
        growth_score * 0.2 +
        min(engagement, 10) * 0.1
    )
    
    return final
```

---

## API 엔드포인트 설계

### GET /api/v1/competitors/channels

**요청**:
```json
{
  "refresh": false  // true면 재분석, false면 캐시 사용
}
```

**응답**:
```json
{
  "my_channel": {
    "id": "UCxxx",
    "title": "코딩알려주는누나",
    "subscriber_count": 118000
  },
  "competitors": [
    {
      "channel_id": "UCyyy",
      "title": "노마드 코더",
      "subscriber_count": 450000,
      "tier": "larger",
      "similarity_score": 85,
      "growth_rate": 0.35,
      "final_score": 72.5,
      "reason": "같은 웹개발 교육 분야, 20대 개발자 타겟 동일",
      "target_audience_inferred": "20대 초반 개발자",
      "thumbnail_url": "https://...",
      "recent_videos_avg_views": 25000,
      "analyzed_at": "2026-02-04T10:00:00Z"
    }
  ],
  "total": 15,
  "cache_expires_at": "2026-02-11T10:00:00Z"  // 7일 캐시
}
```

---

## 데이터 수집 최적화

### 배치 처리
```python
# 한 번에 50개 채널 ID 조회 (YouTube API 제한)
chunks = [channel_ids[i:i+50] for i in range(0, len(channel_ids), 50)]

for chunk in chunks:
    details = await get_channel_details(chunk)
    # ... 처리
```

### 캐싱 전략
```python
# 1. DB에 7일간 캐시
# 2. 같은 쿼리면 재사용
# 3. refresh=true면 강제 재분석

if not refresh:
    cached = await db.execute(
        select(CompetitorChannel)
        .where(CompetitorChannel.reference_channel_id == my_channel_id)
        .where(CompetitorChannel.analyzed_at > datetime.now() - timedelta(days=7))
    )
    if cached:
        return cached
```

### API 할당량 관리
```python
# YouTube Data API 할당량: 일 10,000 units
# - search.list: 100 units
# - channels.list: 1 unit
# - videos.list: 1 unit

# 예산 계산:
# - 5개 검색어 × 20개 = 500 units (search)
# - 100개 채널 조회 = 2 chunks × 1 unit = 2 units
# - 100개 채널 × 20개 영상 = 2000 chunks × 1 unit = 2000 units (videos)
# 
# 총 약 2500 units (하루 4번 실행 가능)
```

---

## 구현 우선순위

### P0 (핵심 기능)
- [x] 내 채널 페르소나 조회
- [ ] AI 검색 쿼리 생성
- [ ] YouTube 채널 검색 (search.list)
- [ ] 채널 상세 정보 조회 (channels.list)
- [ ] AI 유사도 분석
- [ ] 규모 기준 필터링

### P1 (중요 기능)
- [ ] 성장률 분석 (최근 vs 과거 영상)
- [ ] 종합 점수 계산 및 정렬
- [ ] DB 저장 및 캐싱
- [ ] API 엔드포인트 구현

### P2 (부가 기능)
- [ ] 임베딩 기반 유사도 (보조)
- [ ] 경쟁 채널 트렌드 분석
- [ ] 경쟁 채널 콘텐츠 전략 분석
- [ ] 주기적 업데이트 스케줄러

---

## 기술 스택

### Backend
- **YouTube Data API v3**: 채널 검색, 통계 조회
- **OpenAI GPT-4o-mini**: 검색 쿼리 생성, 유사도 분석
- **LangChain**: LLM 오케스트레이션, 임베딩
- **SQLAlchemy**: DB ORM
- **httpx**: 비동기 HTTP 클라이언트

### 데이터 처리
- **pandas** (선택): 통계 계산
- **numpy**: 임베딩 유사도 계산

---

## 예상 결과 예시

```markdown
## 경쟁 유튜버 분석 결과

### 🎯 내 채널
- **코딩알려주는누나**
- 구독자 118,000명
- 주제: AI 코딩, 웹개발, 개발자 교육

---

### 🏆 Top 5 경쟁 채널

#### 1. 노마드 코더 (종합 점수: 85.2)
- **구독자**: 450,000명 (3.8배)
- **Tier**: Larger (벤치마킹 대상)
- **유사도**: 88점
- **성장률**: +35% (최근 30일)
- **이유**: 웹개발 실전 교육, 20대 개발자 타겟 동일. 프로젝트 기반 학습 강조.
- **차별화**: 영어 콘텐츠 다수, 해외 취업 위주

#### 2. 드림코딩 (종합 점수: 82.1)
- **구독자**: 380,000명 (3.2배)
- **Tier**: Larger
- **유사도**: 82점
- **성장률**: +28%
- **이유**: 프론트엔드 교육, 실전 프로젝트 중심, 여성 크리에이터
- **차별화**: React/JavaScript 특화, 포트폴리오 강조

#### 3. 조코딩 (종합 점수: 79.5)
- **구독자**: 620,000명 (5.3배)
- **Tier**: Larger
- **유사도**: 75점
- **성장률**: +15%
- **이유**: 개발 입문자 대상, 쉬운 설명, 트렌디한 기술 다룸
- **차별화**: 게임/앱 개발 비중 높음, 유머러스한 스타일

#### 4. 개발자의품격 (종합 점수: 71.3)
- **구독자**: 85,000명 (0.7배)
- **Tier**: Similar
- **유사도**: 78점
- **성장률**: +65% ⚡ (급성장!)
- **이유**: AI 코딩 활용 교육, 커리어 조언, 유사한 타겟층
- **차별화**: 기업 인사이트 강조, 연봉/이직 정보 집중

#### 5. 얄코 (종합 점수: 69.8)
- **구독자**: 210,000명 (1.8배)
- **Tier**: Larger
- **유사도**: 72점
- **성장률**: +12%
- **이유**: 개발 기초 교육, 친근한 설명, 입문자 타겟
- **차별화**: 애니메이션 활용, 개념 설명 중심
```

---

## 활용 방안

### 1. 벤치마킹
- 경쟁 채널의 인기 영상 분석
- 제목 패턴, 썸네일 전략 학습
- 콘텐츠 아이디어 참고

### 2. 차별화 전략
- 경쟁 채널과 겹치지 않는 주제 발굴
- 내 채널만의 독특한 포지셔닝 강화

### 3. 협업 기회
- 유사 채널과 콜라보 가능성 탐색
- 서로 보완적인 채널 발견

---

## 🚀 구현 일정 (예상)

| Phase | 작업 | 소요 시간 |
|-------|------|-----------|
| 1 | DB 스키마 + 서비스 계층 | 4시간 |
| 2 | AI 검색 쿼리 생성 | 2시간 |
| 3 | YouTube API 채널 검색 | 3시간 |
| 4 | AI 유사도 분석 | 4시간 |
| 5 | 성장률 분석 | 3시간 |
| 6 | 종합 점수 및 API | 2시간 |
| 테스트 | 통합 테스트 및 디버깅 | 3시간 |

**총 예상 시간**: 약 21시간 (3일)

---

## ⚠️ 주의사항

1. **API 할당량**: YouTube API 할당량 초과 방지를 위한 캐싱 필수
2. **개인정보**: 채널 분석 시 개인정보 수집 금지
3. **정확도**: AI 분석 결과는 참고용, 최종 판단은 사용자
4. **업데이트**: 주 1회 재분석 권장 (신규 급성장 채널 포착)

---

## 💡 향후 확장 가능성

- **경쟁 채널 모니터링**: 주간 성장률, 신규 영상 알림
- **콘텐츠 갭 분석**: 경쟁 채널이 다루지 않는 주제 발견
- **협업 추천**: 상호 보완적인 채널 매칭
- **시장 포지셔닝 맵**: 2D 시각화 (규모 vs 성장률)
