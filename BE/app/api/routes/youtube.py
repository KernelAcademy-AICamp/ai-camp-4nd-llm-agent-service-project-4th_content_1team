from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user
from app.models.user import User
from app.schemas.youtube import (
    YouTubePopularSearchRequest,
    YouTubePopularSearchResponse,
    YouTubeVideoItem,
)
from app.services.youtube_service import YouTubeService, YouTubeServiceError


router = APIRouter(prefix="/youtube", tags=["youtube"])


@router.post(
    "/popular-search",
    response_model=YouTubePopularSearchResponse,
    summary="Get popular YouTube videos for given title and keywords",
)
async def popular_search(
    payload: YouTubePopularSearchRequest,
    current_user: User = Depends(get_current_user),
) -> YouTubePopularSearchResponse:
    """
    Search for recent YouTube videos using title + keywords and
    return the top 10 videos ranked by popularity score.

    - 대상 기간: 최근 30일 업로드 영상
    - 점수: views/day + (like_weight * likes/day)
    """
    try:
        items_raw: List[dict] = await YouTubeService.get_popular_videos(
            title=payload.title,
            keywords=payload.keywords,
            days_window=30,
            max_candidates=50,
            top_k=10,
        )
    except YouTubeServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch YouTube videos.",
        )

    items = [
        YouTubeVideoItem(
            video_id=item["video_id"],
            title=item["title"],
            channel_title=item["channel_title"],
            published_at=item["published_at"],
            url=item["url"],
            thumbnail_url=item.get("thumbnail_url"),
            view_count=item.get("view_count", 0),
            like_count=item.get("like_count", 0),
            views_per_day=item["views_per_day"],
            likes_per_day=item["likes_per_day"],
            popularity_score=item["popularity_score"],
        )
        for item in items_raw
    ]

    return YouTubePopularSearchResponse(items=items)

