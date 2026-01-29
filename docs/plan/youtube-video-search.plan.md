# YouTube 트렌드 인기순 비디오 검색 기능 구현 계획

> 생성일: 2026-01-28  
> 상태: Plan 완료  
> PDCA 단계: Plan

---

## 1. 기능 개요

### 핵심 요구사항
- **검색 조건**: keywords (필수) + title (선택) 조합 검색
- **정렬 기준**: 트렌드 인기도 점수 (커스텀 알고리즘)
- **결과 수**: Top 10 비디오 (조정 가능, 최대 50개)

### 비즈니스 가치
- **트렌디한 콘텐츠 발굴**: 단순 조회수가 아닌 성장률 기반 트렌드 파악
- **신선한 레퍼런스**: 최근 업로드 비디오에 높은 가중치 부여
- **품질 중심 선별**: 참여도(좋아요, 댓글) 반영으로 양질의 콘텐츠 우선

---

## 2. 트렌드 인기도 알고리즘 정의

### 핵심 개념
"트렌드 점수" = **(일일 조회수 × 신선도 가중치) + 참여도 점수**

### 수식

```python
popularity_score = (views_per_day × recency_weight) + engagement_score

where:
  views_per_day = viewCount / days_since_upload
  recency_weight = 1 + max(0, (30 - days_since_upload) / 30)
  engagement_score = likeCount × 0.1 + commentCount × 0.05
```

### 세부 로직

#### 1. 일일 조회수 (`views_per_day`)
- **공식**: `viewCount / days_since_upload`
- **0 나누기 방지**: 업로드 당일은 1일로 계산
- **의미**: 시간 대비 조회수 증가율 (트렌드 핵심 지표)

**예시**:
- 2일 전 업로드, 100K 조회수 → 50K/일
- 60일 전 업로드, 1M 조회수 → 16.7K/일

#### 2. 신선도 보너스 (`recency_weight`)
- **공식**: `1 + max(0, (30 - days_since_upload) / 30)`
- **가중치 범위**: 1.0 ~ 2.0
  - 업로드 당일: 2.0배
  - 15일 전: 1.5배
  - 30일 전: 1.0배
  - 30일 이후: 1.0배 (고정)
- **의미**: 최근 업로드일수록 높은 점수 (선형 감소)

**그래프**:
```
가중치
2.0 |●
1.8 |  ●
1.6 |    ●
1.4 |      ●
1.2 |        ●
1.0 |__________●________
    0   10   20   30   60 (일)
```

#### 3. 참여도 점수 (`engagement_score`)
- **공식**: `likeCount × 0.1 + commentCount × 0.05`
- **좋아요 가중치**: 0.1 (댓글보다 2배 중요)
- **댓글 가중치**: 0.05
- **의미**: 시청자 참여도 반영 (품질 지표)

**예시**:
- 좋아요 5K, 댓글 200개 → 500 + 10 = 510점
- 좋아요 50K, 댓글 2K개 → 5,000 + 100 = 5,100점

#### 4. 최종 점수 계산 예시

| 비디오 | 업로드 | 조회수 | 좋아요 | 댓글 | 일일 조회수 | 신선도 | 참여도 | **최종 점수** |
|--------|--------|--------|--------|------|-------------|--------|--------|---------------|
| **A** | 2일 전 | 100K | 5K | 200 | 50,000 | 1.93 | 510 | **97,010** 🥇 |
| **B** | 60일 전 | 1M | 50K | 2K | 16,667 | 1.0 | 5,100 | 21,767 🥉 |
| **C** | 7일 전 | 300K | 15K | 1K | 42,857 | 1.77 | 1,550 | 77,407 🥈 |

**결과**: A (신선+급성장) > C (균형) > B (레거시)

### 알고리즘 특징

✅ **트렌드 중심**: 단순 누적 조회수가 아닌 성장률 기반  
✅ **신선도 우대**: 30일 이내 업로드 비디오에 최대 2배 가중치  
✅ **참여도 반영**: 조회수만으로 판단하지 않고 좋아요/댓글 고려  
✅ **레거시 배제**: 오래된 비디오는 조회수가 높아도 낮은 점수

---

## 3. 검색 쿼리 최적화 전략

### 핵심 질문
**"keywords와 title을 어떻게 조합해야 검색 결과가 많이, 잘 나올까?"**

### 답: `intitle:` 연산자 활용 (균형 전략)

#### 전략 비교

| 방법 | 쿼리 예시 | 결과 수 | 관련성 | 선택 |
|------|-----------|---------|--------|------|
| 단순 공백 | `python tutorial beginner` | 많음 | 낮음 | ❌ |
| OR 연산자 | `python tutorial OR beginner` | 매우 많음 | 매우 낮음 | ❌ |
| 정확한 구문 | `"python tutorial" "beginner"` | 적음 | 매우 높음 | ❌ |
| **intitle:** | `python tutorial intitle:beginner` | **중간** | **높음** | **✅✅** |

#### 구현 로직

```python
def _build_query(keywords: str, title: Optional[str]) -> str:
    """
    균형잡힌 검색 쿼리 생성.
    - keywords: 넓은 범위 검색 (컨텐츠 전체)
    - title: intitle: 연산자로 제목 필터링 (관련성 향상)
    """
    if not title:
        return keywords
    
    # title에 공백이 있으면 따옴표로 감싸서 정확한 구문 검색
    if " " in title:
        return f'{keywords} intitle:"{title}"'
    else:
        return f"{keywords} intitle:{title}"
```

#### 실제 예시

| Input | Output Query | 의미 | 예상 결과 |
|-------|--------------|------|-----------|
| keywords="python tutorial"<br>title="beginner" | `python tutorial intitle:beginner` | "python tutorial" 포함 **AND** 제목에 "beginner" | 30-50개 (높은 관련성) |
| keywords="python"<br>title="for beginners" | `python intitle:"for beginners"` | "python" 포함 **AND** 제목에 정확히 "for beginners" | 20-40개 (매우 높은 관련성) |
| keywords="파이썬 강의"<br>title="초보자" | `파이썬 강의 intitle:초보자` | 한국어도 동일 작동 | 20-30개 |

### 왜 이 전략이 좋은가?

✅ **충분한 결과 수**: keywords로 넓게 수집 (50개 목표)  
✅ **높은 관련성**: title이 제목에 있어야 하므로 주제 일치도 ↑  
✅ **유연성**: title 없이도 동작  
✅ **구문 정확도**: 공백 포함 시 자동 따옴표 처리  
✅ **다국어 지원**: 한국어, 영어 모두 작동

---

## 4. 시스템 아키텍처

### 데이터 흐름

```
Client Request
     │
     ▼
FastAPI Router (/api/v1/youtube/search)
     │
     ▼
YouTubeService.search_popular_videos()
     │
     ├─── 1. _build_query(keywords, title)
     │         └─► "python tutorial intitle:beginner"
     │
     ├─── 2. _search_video_ids() [100 units]
     │         └─► YouTube search.list API
     │              └─► [video_id_1, video_id_2, ...]
     │
     ├─── 3. _get_video_details() [1 unit]
     │         └─► YouTube videos.list API
     │              └─► [{snippet, statistics}, ...]
     │
     ├─── 4. _calculate_popularity_score() ⭐
     │         └─► 각 비디오별 트렌드 점수 계산
     │
     └─── 5. Sort & Slice
               └─► Top 10 비디오 반환
                    │
                    ▼
               VideoSearchResponse
```

### 레이어 구조

| 레이어 | 파일 | 상태 | 역할 |
|--------|------|------|------|
| **Frontend** | `FE/src/lib/api.ts` | 수정 | API 호출 함수 추가 |
| **Router** | `BE/app/api/routes/youtube.py` | 신규 | HTTP 엔드포인트 |
| **Schema** | `BE/app/schemas/youtube.py` | 신규 | 요청/응답 모델 |
| **Service** | `BE/app/services/youtube_service.py` | 수정 | 검색 + 알고리즘 로직 |
| **Config** | `BE/app/core/config.py` | 수정 | YouTube API 키 추가 |

---

## 5. API 설계

### 5.1 엔드포인트

```
POST /api/v1/youtube/search
Content-Type: application/json
```

### 5.2 Request

```json
{
  "keywords": "python tutorial",
  "title": "beginner",
  "max_results": 10
}
```

| 필드 | 타입 | 필수 | 제약 | 설명 |
|------|------|------|------|------|
| `keywords` | string | ✅ | 1-100자 | 검색 키워드 |
| `title` | string | ❌ | 최대 100자 | 제목 필터 |
| `max_results` | integer | ❌ | 1-50 | 반환 개수 (기본 10) |

### 5.3 Response

```json
{
  "total_results": 10,
  "query": "python tutorial beginner",
  "videos": [
    {
      "video_id": "abc123",
      "title": "Python Tutorial for Beginners",
      "description": "Learn Python in 2026...",
      "thumbnail_url": "https://i.ytimg.com/vi/abc123/mqdefault.jpg",
      "channel_id": "UCxyz",
      "channel_title": "Code Academy",
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

### 5.4 Error Responses

| Status | 상황 | 응답 |
|--------|------|------|
| 200 | 성공 | VideoSearchResponse |
| 400 | keywords 누락 | `{"detail": "keywords는 필수입니다"}` |
| 422 | 유효성 실패 | Pydantic 에러 상세 |
| 429 | API 할당량 초과 | `{"detail": "YouTube API 일일 할당량 초과"}` |
| 504 | 타임아웃 | `{"detail": "YouTube API 요청 시간 초과"}` |
| 500 | 서버 에러 | `{"detail": "비디오 검색 중 오류 발생"}` |

---

## 6. 구현 체크리스트

### Phase 1: 환경 설정 (30분)
- [ ] Google Cloud Console에서 YouTube Data API v3 활성화
- [ ] API 키 생성
- [ ] `config.py`에 `youtube_api_key` 추가
- [ ] `.env` 파일 업데이트
- [ ] curl로 API 테스트

### Phase 2: Schema 정의 (30분)
- [ ] `BE/app/schemas/youtube.py` 생성
- [ ] `VideoSearchRequest` 스키마 작성
- [ ] `VideoItem` 스키마 (`popularity_score`, `days_since_upload` 포함)
- [ ] `VideoSearchResponse` 스키마 작성
- [ ] Validator 작성

### Phase 3: Service 로직 (2시간)
- [ ] `_calculate_popularity_score()` 구현 ⭐ 핵심 알고리즘
- [ ] `search_popular_videos()` 구현
- [ ] `_build_query()` - 검색 쿼리 최적화
- [ ] `_search_video_ids()` - search.list API
- [ ] `_get_video_details()` - videos.list API
- [ ] 에러 핸들링

### Phase 4: API Router (30분)
- [ ] `BE/app/api/routes/youtube.py` 생성
- [ ] `POST /api/v1/youtube/search` 구현
- [ ] `main.py`에 라우터 등록
- [ ] Swagger UI 테스트

### Phase 5: Frontend (30분)
- [ ] `FE/src/lib/api.ts`에 타입 정의
- [ ] `searchYouTubeVideos()` 함수 구현

### Phase 6: 테스트 (2시간)
- [ ] Mock 데이터 작성
- [ ] 알고리즘 단위 테스트 (특히 점수 계산)
- [ ] API 통합 테스트
- [ ] 정렬 검증 테스트
- [ ] 에러 케이스 테스트

### Phase 7: 문서화 (30분)
- [ ] API docstring 작성
- [ ] 알고리즘 설명 주석
- [ ] README 업데이트

**총 예상 시간**: 약 7시간

---

## 7. API 비용 분석

### YouTube Data API v3 할당량

| 작업 | 비용 |
|------|------|
| `search.list` | 100 units |
| `videos.list` | 1 unit |
| **검색 1회** | **101 units** |

**일일 할당량**: 10,000 units → **약 99회 검색 가능**

### 최적화 방안 (향후 확장)

#### Redis 캐싱
```python
cache_key = f"youtube:search:{hash(query)}:{max_results}"
ttl = 3600  # 1시간
```

**효과**: 동일 쿼리 재검색 시 API 호출 0 → **40% 절감 예상**

---

## 8. 성공 기준

✅ **기능적 요구사항**
- keywords + title 조합 검색 동작
- 트렌드 알고리즘 정확히 구현
- Top 10 결과 반환

✅ **성능 요구사항**
- 응답 시간 3초 이내
- API 호출 성공률 95% 이상

✅ **품질 요구사항**
- 단위 테스트 커버리지 80% 이상
- 알고리즘 정렬 검증 통과
- 에러 핸들링 완비

---

## 9. 다음 단계

- [ ] `/pdca design youtube-trend-search` - Design 문서 작성
- [ ] Phase 1부터 구현 시작

---

**Sources**:
- [YouTube Data API v3](https://developers.google.com/youtube/v3/docs)
- [Search: list API](https://developers.google.com/youtube/v3/docs/search/list)
- [Videos: list API](https://developers.google.com/youtube/v3/docs/videos/list)
