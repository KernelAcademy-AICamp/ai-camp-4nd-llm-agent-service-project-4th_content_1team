from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.competitor import (
    CompetitorSaveRequest,
    CompetitorSaveResponse,
    FetchCommentsRequest,
    FetchCommentsResponse,
    VideoCommentSampleOut,
)
from app.services.competitor_service import CompetitorService

router = APIRouter(prefix="/api/v1/competitor", tags=["Competitor"])


@router.post("/save", response_model=CompetitorSaveResponse)
async def save_competitor_videos(
    request: CompetitorSaveRequest,
    db: AsyncSession = Depends(get_db),
):
    """경쟁 영상 컬렉션 저장."""
    try:
        collection = await CompetitorService.save_collection(db, request)
        return CompetitorSaveResponse(
            collection_id=collection.id,
            generated_at=collection.generated_at,
            video_count=len(collection.videos),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"저장 실패: {str(e)}")


@router.post("/comments/fetch", response_model=FetchCommentsResponse)
async def fetch_video_comments(
    request: FetchCommentsRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    가장 최상위 영상의 댓글을 좋아요, 싫어요, 하트 순으로 가져와서 DB에 저장.
    
    - competitor_video_id: 경쟁 영상 ID
    - max_results: 가져올 댓글 수 (기본 10개, 최대 100개)
    """
    try:
        comment_samples = await CompetitorService.fetch_and_save_comments(
            db,
            request.competitor_video_id,
            max_results=request.max_results,
        )
        
        return FetchCommentsResponse(
            competitor_video_id=request.competitor_video_id,
            comment_count=len(comment_samples),
            comments=[
                VideoCommentSampleOut(
                    id=comment.id,
                    competitor_video_id=comment.competitor_video_id,
                    comment_id=comment.comment_id,
                    text=comment.text,
                    likes=comment.likes,
                    published_at=comment.published_at,
                )
                for comment in comment_samples
            ],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"댓글 가져오기 실패: {str(e)}")
