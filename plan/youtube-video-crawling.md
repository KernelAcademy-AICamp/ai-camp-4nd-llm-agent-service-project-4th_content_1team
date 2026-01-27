# YouTube 영상 크롤링 기능 구현 계획

> 생성일: 2026-01-27
> 상태: 계획 완료

## 1. 현재 프로젝트 상태 분석

### 기존 코드 파악

**데이터베이스 구조**

- PostgreSQL + SQLAlchemy ORM 사용
- YouTube 채널 정보 저장 (`BE/app/models/youtube_channel.py`)
- 5개 테이블: YouTubeChannel, YTChannelStatsDaily, YTChannelTopic, YTAudienceDaily, YTGeoDaily

**기존 YouTube 연동**

- YouTubeService 클래스 (`BE/app/services/youtube_service.py`)
- YouTube Data API v3 사용 (BASE_URL: https://www.googleapis.com/youtube/v3)
- 현재는 사용자 본인의 채널 정보만 가져오는 기능 (mine=true)
- httpx 라이브러리로 비동기 HTTP 요청 처리

**인증 시스템**

- Google OAuth 2.0 로그인 구현
- access_token을 통한 YouTube API 인증
- 로그인 시 채널 정보 자동 동기화

---

## 2. YouTube Data API v3를 사용한 영상 검색

### API 엔드포인트

| API         | URL       | 용도           | 쿼터      |
| ----------- | --------- | -------------- | --------- |
| search.list | `/search` | 영상 검색      | 100 units |
| videos.list | `/videos` | 영상 상세 정보 | 1 unit    |

### 주요 파라미터

**search.list**

- `part`: snippet (필수)
- `q`: 검색어
- `type`: video
- `order`: date, rating, relevance, title, videoCount, viewCount
- `maxResults`: 1-50

**videos.list**

- `part`: snippet, statistics, contentDetails
- `id`: 비디오 ID (쉼표로 구분, 최대 50개)

### API 쿼터 고려사항

- 일일 쿼터: 10,000 units (기본)
- 최적화: 필요한 part만 요청, 결과 캐싱

---

## 3. 검색 쿼리 구성 방법

### topic_title과 topic_keywords 활용 전략

```python
# 방법 3: OR 연산 (재현율 우선)
query = f"{topic_title} | {' | '.join(topic_keywords)}"
# 예: "AI 코딩 교육 | 파이썬 | 머신러닝"
```

### 추가 필터링 옵션

- `publishedAfter`: 특정 날짜 이후 영상
- `regionCode`: 지역 제한
- `relevanceLanguage`: 언어 필터
- `videoDuration`: 영상 길이 (short, medium, long)
- `videoDefinition`: HD 여부

---

## 4. 인기순 정렬 방법

### 정렬 옵션 비교

| order 파라미터 | 설명      | 사용 사례           |
| -------------- | --------- | ------------------- |
| viewCount      | 조회수 순 | 가장 인기 있는 영상 |
| rating         | 평점 순   | 좋아요가 많은 영상  |
| relevance      | 관련성 순 | 검색어 매칭 최적화  |
| date           | 최신순    | 트렌드 파악         |

### 복합 정렬 전략 (권장)

1. API에서 `viewCount`로 정렬하여 검색
2. `videos.list`로 상세 정보 조회
3. 애플리케이션 레벨에서 복합 점수 계산:

```python
점수 = (viewCount * 0.4) + (likeCount * 0.3) + (commentCount * 0.2) + (최신성 * 0.1)
```

---

## 5. 크롤링 결과 데이터 구조 설계

### 새로운 테이블

**파일 위치**: `BE/app/models/youtube_video.py`

```python
class YTVideoSearch(Base):
    """YouTube 영상 검색 결과"""
    __tablename__ = "yt_video_searches"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # 검색 정보
    topic_title = Column(String, nullable=False)
    topic_keywords = Column(String, nullable=True)  # 쉼표로 구분
    search_query = Column(String, nullable=False)  # 실제 사용된 검색어

    # 메타데이터
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    videos = relationship("YTVideo", back_populates="search", cascade="all, delete-orphan")


class YTVideo(Base):
    """YouTube 영상 상세 정보"""
    __tablename__ = "yt_videos"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    video_id = Column(String, nullable=False, unique=True)  # YouTube video ID
    search_id = Column(UUID, ForeignKey("yt_video_searches.id", ondelete="CASCADE"), nullable=False)

    # 기본 정보
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    channel_id = Column(String, nullable=False)
    channel_title = Column(String, nullable=False)
    published_at = Column(DateTime, nullable=False)

    # 통계 정보
    view_count = Column(BigInteger, nullable=True)
    like_count = Column(Integer, nullable=True)
    comment_count = Column(Integer, nullable=True)

    # 썸네일
    thumbnail_url = Column(String, nullable=True)

    # 메타데이터
    duration = Column(String, nullable=True)  # ISO 8601 형식
    tags = Column(ARRAY(String), nullable=True)

    # 원본 JSON 저장 (디버깅/확장용)
    raw_video_json = Column(JSONB, nullable=True)
    raw_stats_json = Column(JSONB, nullable=True)

    # 인기 점수 (정렬용)
    popularity_score = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    search = relationship("YTVideoSearch", back_populates="videos")
```

### Pydantic 스키마

**파일 위치**: `BE/app/schemas/youtube.py`

```python
class VideoSearchRequest(BaseModel):
    """영상 검색 요청"""
    topic_title: str = Field(..., min_length=1, max_length=200)
    topic_keywords: Optional[List[str]] = Field(default=None, max_items=10)
    max_results: int = Field(default=10, ge=1, le=50)
    order_by: str = Field(default="viewCount", regex="^(viewCount|rating|relevance|date)$")
    published_after: Optional[datetime] = None
    video_duration: Optional[str] = Field(default=None, regex="^(short|medium|long)$")


class VideoResponse(BaseModel):
    """영상 정보 응답"""
    video_id: str
    title: str
    description: Optional[str]
    channel_id: str
    channel_title: str
    published_at: datetime
    view_count: Optional[int]
    like_count: Optional[int]
    comment_count: Optional[int]
    thumbnail_url: Optional[str]
    duration: Optional[str]
    popularity_score: Optional[float]


class VideoSearchResponse(BaseModel):
    """검색 결과 응답"""
    search_id: str
    topic_title: str
    topic_keywords: Optional[List[str]]
    total_results: int
    videos: List[VideoResponse]
    created_at: datetime
```

---

## 6. API 엔드포인트 설계

**파일 위치**: `BE/app/api/routes/youtube.py`

| Method | Endpoint                                      | 설명           |
| ------ | --------------------------------------------- | -------------- |
| POST   | `/api/v1/youtube/videos/search`               | 영상 검색      |
| GET    | `/api/v1/youtube/videos/searches/{search_id}` | 검색 결과 조회 |
| GET    | `/api/v1/youtube/videos/searches`             | 검색 이력 조회 |

### 라우터 코드

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/youtube", tags=["youtube"])

@router.post("/videos/search", response_model=VideoSearchResponse)
async def search_videos(
    request: VideoSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """topic_title과 topic_keywords로 YouTube 영상 검색"""
    result = await YouTubeSearchService.search_and_save_videos(
        db=db,
        user_id=current_user.id,
        topic_title=request.topic_title,
        topic_keywords=request.topic_keywords,
        max_results=request.max_results,
        order_by=request.order_by,
        published_after=request.published_after,
        video_duration=request.video_duration
    )
    return result
```

---

## 7. 구현 순서와 단계별 작업 목록

### Phase 1: 환경 변수 설정

- [ ] Google Cloud Console에서 YouTube Data API v3 활성화
- [ ] API 키 생성 및 `.env` 파일에 추가
- [ ] `config.py`에 `youtube_api_key` 설정 추가

### Phase 2: 데이터베이스 스키마 구현

- [ ] `BE/app/models/youtube_video.py` 생성
- [ ] `BE/app/models/__init__.py` 업데이트
- [ ] Alembic 마이그레이션 생성 및 실행

### Phase 3: Pydantic 스키마 정의

- [ ] `BE/app/schemas/youtube.py` 생성
- [ ] 요청/응답 모델 정의
- [ ] 유효성 검증 로직 추가

### Phase 4: YouTube 검색 서비스 구현

- [ ] `BE/app/services/youtube_search_service.py` 생성
- [ ] `search_videos()` - YouTube API search.list 호출
- [ ] `get_video_details()` - YouTube API videos.list 호출
- [ ] `calculate_popularity_score()` - 인기 점수 계산
- [ ] `build_search_query()` - 검색어 생성
- [ ] 데이터베이스 저장 로직

### Phase 5: API 라우터 구현

- [ ] `BE/app/api/routes/youtube.py` 생성
- [ ] 엔드포인트 3개 구현
- [ ] `main.py`에 라우터 등록

### Phase 6: 테스트

- [ ] 단위 테스트 작성
- [ ] 통합 테스트 작성
- [ ] 실제 API 테스트

### Phase 7: 최적화

- [ ] 중복 검색 방지 (24시간 캐싱)
- [ ] API 쿼터 관리
- [ ] 배치 처리 최적화

### Phase 8: 프론트엔드 연동

- [ ] Swagger UI 문서 확인
- [ ] CORS 설정 확인
- [ ] TypeScript 타입 생성 (선택)

---

## 8. 고려사항

### 보안

- YouTube API 키는 환경 변수로 관리, 절대 커밋 금지
- 사용자 인증 필수 (`get_current_user` 의존성)
- Rate limiting 구현으로 API 남용 방지

### 확장성

- 검색 결과 페이지네이션 지원
- `nextPageToken` 저장으로 추가 결과 로드
- 백그라운드 작업으로 대량 검색 처리 (Celery 등)

### 성능

- `popularity_score`에 인덱스 추가
- 검색 결과 캐싱 (Redis 도입 고려)

### 모니터링

- YouTube API 쿼터 사용량 로깅
- 검색 실패 사유 추적
- 응답 시간 측정

---

## 9. 핵심 서비스 코드 스니펫

```python
class YouTubeSearchService:
    BASE_URL = "https://www.googleapis.com/youtube/v3"

    @staticmethod
    async def search_and_save_videos(
        db: AsyncSession,
        user_id: UUID,
        topic_title: str,
        topic_keywords: Optional[List[str]] = None,
        max_results: int = 10,
        order_by: str = "viewCount",
        published_after: Optional[datetime] = None,
        video_duration: Optional[str] = None
    ) -> VideoSearchResponse:
        # 1. 검색어 구성
        search_query = YouTubeSearchService._build_search_query(
            topic_title, topic_keywords
        )

        # 2. YouTube API 검색
        search_results = await YouTubeSearchService._search_videos(
            search_query, max_results, order_by, published_after, video_duration
        )

        # 3. 영상 상세 정보 조회
        video_ids = [item["id"]["videoId"] for item in search_results["items"]]
        video_details = await YouTubeSearchService._get_video_details(video_ids)

        # 4. 인기 점수 계산 및 정렬
        enriched_videos = YouTubeSearchService._enrich_and_score_videos(
            search_results["items"], video_details["items"]
        )

        # 5. 데이터베이스 저장
        search_record = await YouTubeSearchService._save_search_result(
            db, user_id, topic_title, topic_keywords, search_query, enriched_videos
        )

        return search_record

    @staticmethod
    def _build_search_query(title: str, keywords: Optional[List[str]]) -> str:
        if not keywords:
            return title
        return f"{title} {' '.join(keywords)}"

    @staticmethod
    def _calculate_popularity_score(
        view_count: int,
        like_count: int,
        comment_count: int,
        published_at: datetime
    ) -> float:
        view_score = (view_count or 0) * 0.4
        like_score = (like_count or 0) * 0.3
        comment_score = (comment_count or 0) * 0.2

        days_old = (datetime.utcnow() - published_at).days
        recency_score = max(0, (365 - days_old) / 365) * 1000

        return view_score + like_score + comment_score + recency_score
```

---

## 10. 생성/수정할 파일 목록

| 파일 경로                                     | 작업 | 설명                        |
| --------------------------------------------- | ---- | --------------------------- |
| `BE/app/models/youtube_video.py`              | 생성 | YTVideoSearch, YTVideo 모델 |
| `BE/app/models/__init__.py`                   | 수정 | 새 모델 등록                |
| `BE/app/schemas/youtube.py`                   | 생성 | Pydantic 스키마             |
| `BE/app/services/youtube_search_service.py`   | 생성 | 검색 서비스 로직            |
| `BE/app/api/routes/youtube.py`                | 생성 | API 라우터                  |
| `BE/app/main.py`                              | 수정 | 라우터 등록                 |
| `BE/app/core/config.py`                       | 수정 | API 키 설정 추가            |
| `BE/.env`                                     | 수정 | YOUTUBE_API_KEY 추가        |
| `BE/alembic/versions/xxx_add_video_tables.py` | 생성 | DB 마이그레이션             |
