# YouTube 트렌드 검색 API 가이드

## 개요

YouTube 비디오를 **트렌드 인기도 알고리즘** 기준으로 검색하는 API입니다.

### 핵심 특징
- ✅ **트렌드 중심**: 단순 조회수가 아닌 성장률 기반
- ✅ **신선도 우대**: 최근 30일 이내 업로드 비디오에 최대 2배 가중치
- ✅ **참여도 반영**: 좋아요, 댓글 수 고려
- ✅ **검색 최적화**: intitle: 연산자로 관련성 높은 결과

---

## 엔드포인트

```
POST /api/v1/youtube/search
```

---

## 요청 (Request)

### Headers
```
Content-Type: application/json
```

### Body

| 필드 | 타입 | 필수 | 제약 | 설명 |
|------|------|------|------|------|
| `keywords` | string | ✅ | 1-100자 | 검색 키워드 |
| `title` | string | ❌ | 최대 100자 | 제목 필터 (intitle: 연산자 사용) |
| `max_results` | integer | ❌ | 1-50 | 반환 개수 (기본 10) |

### 예시

```json
{
  "keywords": "python tutorial",
  "title": "beginner",
  "max_results": 10
}
```

---

## 응답 (Response)

### 성공 (200 OK)

```json
{
  "total_results": 10,
  "query": "python tutorial beginner",
  "videos": [
    {
      "video_id": "abc123",
      "title": "Python Tutorial for Beginners - Full Course",
      "description": "Learn Python programming...",
      "thumbnail_url": "https://i.ytimg.com/vi/abc123/mqdefault.jpg",
      "channel_id": "UCxyz",
      "channel_title": "Programming with Mosh",
      "published_at": "2026-01-26T10:00:00+00:00",
      "statistics": {
        "view_count": 150000,
        "like_count": 8000,
        "comment_count": 350
      },
      "popularity_score": 95347.5,
      "days_since_upload": 2
    }
  ]
}
```

### 에러 응답

| Status | 상황 | 응답 |
|--------|------|------|
| 400 | keywords 누락 | `{"detail": "keywords는 필수입니다"}` |
| 422 | 유효성 실패 | Pydantic 에러 상세 |
| 429 | API 할당량 초과 | `{"detail": "YouTube API 일일 할당량 초과"}` |
| 504 | 타임아웃 | `{"detail": "YouTube API 요청 시간 초과"}` |
| 500 | 서버 에러 | `{"detail": "비디오 검색 중 오류 발생"}` |

---

## 트렌드 인기도 알고리즘

### 수식

```
popularity_score = (views_per_day × recency_weight) + engagement_score
```

### 구성 요소

#### 1. 일일 조회수 (`views_per_day`)
```python
views_per_day = viewCount / days_since_upload
```
- 시간 대비 조회수 증가율
- 0으로 나누기 방지: 업로드 당일은 1일로 계산

#### 2. 신선도 가중치 (`recency_weight`)
```python
recency_weight = 1 + max(0, (30 - days_since_upload) / 30)
```
- 범위: 1.0 ~ 2.0
- 업로드 당일: 2.0배
- 15일 전: 1.5배
- 30일 전: 1.0배
- 30일 이후: 1.0배 (고정)

#### 3. 참여도 점수 (`engagement_score`)
```python
engagement_score = likeCount × 0.1 + commentCount × 0.05
```
- 좋아요가 댓글보다 2배 중요

### 예시 계산

| 비디오 | 업로드 | 조회수 | 좋아요 | 댓글 | 일일 조회수 | 신선도 | 참여도 | **최종 점수** |
|--------|--------|--------|--------|------|-------------|--------|--------|---------------|
| A | 2일 전 | 100K | 5K | 200 | 50,000 | 1.93 | 510 | **97,010** 🥇 |
| B | 60일 전 | 1M | 50K | 2K | 16,667 | 1.0 | 5,100 | 21,767 🥉 |
| C | 7일 전 | 300K | 15K | 1K | 42,857 | 1.77 | 1,550 | 77,407 🥈 |

**결과**: A (신선+급성장) > C (균형) > B (레거시)

---

## 검색 쿼리 전략

### intitle: 연산자 활용

#### 동작 방식
- **keywords**: 넓은 범위 검색 (비디오 전체 내용)
- **title**: `intitle:` 연산자로 제목만 필터링

#### 예시

| Input | 생성된 쿼리 | 의미 |
|-------|-------------|------|
| keywords="python tutorial"<br>title=None | `python tutorial` | keywords만 검색 |
| keywords="python tutorial"<br>title="beginner" | `python tutorial intitle:beginner` | "python tutorial" 포함 **AND** 제목에 "beginner" |
| keywords="python"<br>title="for beginners" | `python intitle:"for beginners"` | "python" 포함 **AND** 제목에 정확히 "for beginners" |

#### 장점
✅ **충분한 결과 수**: keywords로 넓게 수집  
✅ **높은 관련성**: title이 제목에 있어야 함  
✅ **유연성**: title 없이도 동작  
✅ **다국어 지원**: 한국어, 영어 모두 작동

---

## 사용 예시

### cURL

```bash
curl -X POST "http://localhost:8000/api/v1/youtube/search" \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": "python tutorial",
    "title": "beginner",
    "max_results": 10
  }'
```

### Python (requests)

```python
import requests

url = "http://localhost:8000/api/v1/youtube/search"
payload = {
    "keywords": "python tutorial",
    "title": "beginner",
    "max_results": 10
}

response = requests.post(url, json=payload)
result = response.json()

for video in result["videos"]:
    print(f"{video['title']} - Score: {video['popularity_score']:.2f}")
```

### JavaScript (Fetch)

```javascript
const response = await fetch('http://localhost:8000/api/v1/youtube/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    keywords: 'python tutorial',
    title: 'beginner',
    max_results: 10
  })
});

const result = await response.json();
console.log(`Found ${result.total_results} videos`);
```

---

## API 비용 분석

### YouTube Data API v3 할당량

| 작업 | 비용 |
|------|------|
| `search.list` | 100 units |
| `videos.list` | 1 unit |
| **검색 1회** | **101 units** |

**일일 할당량**: 10,000 units → **약 99회 검색 가능**

---

## 환경 설정

### 1. YouTube API 키 발급

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 프로젝트 선택 또는 생성
3. "API 및 서비스" → "라이브러리"
4. "YouTube Data API v3" 검색 후 활성화
5. "사용자 인증 정보" → "API 키 만들기"
6. 생성된 키를 복사

### 2. 환경 변수 설정

`.env` 파일에 추가:

```env
YOUTUBE_API_KEY=your_youtube_api_key_here
```

---

## Swagger UI

FastAPI의 자동 문서화 기능으로 브라우저에서 테스트 가능:

```
http://localhost:8000/docs
```

"YouTube" 섹션에서 `/api/v1/youtube/search` 엔드포인트 확인 및 테스트

---

## 참고 자료

- [YouTube Data API v3 공식 문서](https://developers.google.com/youtube/v3/docs)
- [search.list API](https://developers.google.com/youtube/v3/docs/search/list)
- [videos.list API](https://developers.google.com/youtube/v3/docs/videos/list)
