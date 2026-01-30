from fastapi import APIRouter, HTTPException
from datetime import datetime

from app.schemas.youtube import (
    VideoSearchRequest,
    VideoSearchResponse,
    VideoItem,
    VideoStatistics
)
from app.services.youtube_service import YouTubeService
from app.core.config import settings

router = APIRouter(prefix="/api/v1/youtube", tags=["YouTube"])


@router.post("/search", response_model=VideoSearchResponse)
async def search_videos(request: VideoSearchRequest):
    """
    트렌드 인기도 기준 YouTube 비디오 검색.
    
    ### 알고리즘
    - **popularity_score** = (일일 조회수 × 신선도 가중치) + 참여도
    - **일일 조회수**: viewCount / days_since_upload
    - **신선도 가중치**: 30일 이내 업로드 시 최대 2배 (선형 감소)
    - **참여도**: likeCount × 0.1 + commentCount × 0.05
    
    ### 검색 쿼리 전략
    - **keywords**: 넓은 범위 검색 (비디오 전체 내용)
    - **title**: intitle: 연산자로 제목 필터링 (관련성 향상)
    
    ### 예시
    ```json
    {
      "keywords": "python tutorial",
      "title": "beginner",
      "max_results": 10
    }
    ```
    → 검색 쿼리: `python tutorial intitle:beginner`
    
    ### 응답
    - 트렌드 인기도 점수 기준 내림차순 정렬
    - 최대 50개까지 요청 가능 (기본 10개)
    """
    try:
        # YouTube API를 통해 비디오 검색
        raw_videos = await YouTubeService.search_popular_videos(
            keywords=request.keywords,
            title=request.title,
            max_results=request.max_results,
            api_key=settings.youtube_api_key
        )
        
        # Raw 데이터를 Pydantic 모델로 변환
        videos = []
        for v in raw_videos:
            snippet = v.get("snippet", {})
            stats = v.get("statistics", {})
            content_details = v.get("contentDetails", {})

            try:
                video_item = VideoItem(
                    video_id=v["id"],
                    title=snippet.get("title", ""),
                    description=snippet.get("description", ""),
                    thumbnail_url=snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                    channel_id=snippet.get("channelId", ""),
                    channel_title=snippet.get("channelTitle", ""),
                    published_at=datetime.fromisoformat(
                        snippet.get("publishedAt", "").replace("Z", "+00:00")
                    ),
                    statistics=VideoStatistics(
                        view_count=int(stats.get("viewCount", 0)),
                        like_count=int(stats.get("likeCount", 0)),
                        comment_count=int(stats.get("commentCount", 0))
                    ),
                    popularity_score=v.get("popularity_score", 0.0),
                    days_since_upload=v.get("days_since_upload", 0),
                    has_caption=content_details.get("caption", "false") == "true"
                )
                videos.append(video_item)
            except (ValueError, KeyError) as e:
                # 개별 비디오 파싱 실패 시 스킵
                continue
        
        # 실제 사용된 검색 쿼리
        query = f"{request.keywords} {request.title}" if request.title else request.keywords
        
        return VideoSearchResponse(
            total_results=len(videos),
            query=query,
            videos=videos
        )
        
    except HTTPException:
        # YouTubeService에서 발생한 HTTPException은 그대로 전달
        raise
    except Exception as e:
        # 예상치 못한 에러
        raise HTTPException(
            status_code=500,
            detail=f"검색 실패: {str(e)}"
        )
