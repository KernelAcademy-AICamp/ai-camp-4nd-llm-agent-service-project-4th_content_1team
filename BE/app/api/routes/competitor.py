from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.competitor import CompetitorSaveRequest, CompetitorSaveResponse
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
