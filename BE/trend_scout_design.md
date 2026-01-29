# 레딧 트렌드 스카우트 (Trend Scout) 설계안

## 1. 개요
API 키 없이 레딧의 공개 JSON URL(`Example.json`)을 활용하여 실시간 인기 글을 수집하고, GPT-4o를 통해 사용자 채널 성격(페르소나)에 맞는 뉴스 검색 키워드를 추출하는 노드입니다.

## 2. 워크플로우

### 1단계: 타겟 게시판 선정 (Targeting)
사용자의 `state["channel_profile"]["topics"]` 정보에 따라 긁어올 게시판(Subreddit)을 자동 매핑합니다.

**[예외 처리 - 페르소나 데이터가 없을 경우]**
- **전략**: 대중적인 "Global Issue" 수집으로 전환
- **타겟**: `r/popular` (전체 인기글), `r/todayilearned` (오늘의 상식), `r/worldnews` (세계 뉴스)

**[정상 케이스 매핑 예시]**
- **Tech/AI**: `r/technology`, `r/gadgets`, `r/artificial`
- **Finance**: `r/investing`, `r/stocks`, `r/economics`
- **Gaming**: `r/gaming`, `r/Games`, `r/pcgaming`

### 2단계: 데이터 수집 (Fetching)
- **방식**: HTTP GET Request (API Key 불필요)
- **URL 패턴**: `https://www.reddit.com/r/{subreddit}/hot.json?limit=50`
- **필수 헤더**: `User-Agent`를 일반 브라우저(Chrome/Mozilla)처럼 위장하여 429 차단 방지.
- **수집 항목**:
  - 제목 (title)
  - 추천 수 (score)
  - 댓글 수 (num_comments)
  - 원본 링크 (url)

### 3단계: AI 필터링 (Filtering)
수집된 50~100개의 글 중에서 **"우리 채널에서 다룰만한 소재"**만 선별합니다.
- **Input**: 수집된 글 리스트 + 사용자 채널 페르소나
- **Model**: GPT-4o-mini
- **Task**:
  1. 단순 유머, 혐오, 정치 등 부적절한 글 제외
  2. 채널 주제와 연관성 높은 글 Top 3~5 선정
  3. 선정된 주제를 **"한국어 뉴스 검색용 키워드"**로 변환

**[페르소나 정보 부재 시 Fallback 전략]**
- 전문성보다는 **"논쟁이 활발하고(댓글 수↑), 한국에서도 관심 가질만한(Global) 키워드"** 위주로 추출하도록 프롬프트 자동 조정.

### 4단계: 결과 전달 (Output)
- **Output State**: `researchPlan.newsQuery`에 키워드 리스트 저장.
- **최후의 보루 (Safety Net)**: 레딧 접속 실패 시, 하드코딩된 기본 키워드("최신 뉴스 트렌드" 등)를 반환하여 파이프라인 중단 방지.
- 이후 `news_research` 노드가 이 키워드를 받아 심층 조사를 시작함.

## 3. 데이터 인터페이스 (Interface Contract)
다른 팀원이 개발하는 페르소나 에이전트와의 연동 규격입니다.

```python
# 입력 State 예시 (Optional)
state["channel_profile"] = {
    "topics": ["AI", "반도체"],    # 필수 아님 (없으면 기본값 동작)
    "tone": "전문적인",
    "target_audience": "30대"
}
```

## 4. 예시 시나리오
- **채널 주제**: "최신 AI 뉴스"
- **레딧 1위 글**: "고양이가 춤추는 영상" (Score: 50k) -> **제외** (주제 불일치)
- **레딧 5위 글**: "OpenAI, 동영상 생성 모델 Sora 공개" (Score: 10k) -> **선택**
- **최종 키워드**: `["OpenAI Sora 공개", "소라 AI 모델 기능", "Sora 동영상 생성 원리"]`
