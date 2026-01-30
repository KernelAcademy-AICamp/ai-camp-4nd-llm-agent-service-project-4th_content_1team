from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.subtitle import SubtitleFetchRequest, SubtitleFetchResponse
from app.services.subtitle_service import SubtitleService

router = APIRouter(prefix="/api/v1/subtitle", tags=["Subtitle"])


@router.post("/fetch", response_model=SubtitleFetchResponse)
async def fetch_subtitles(
    request: SubtitleFetchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    YouTube 영상 자막 조회 (Innertube 방식).
    영상 ID 리스트를 받아 각 영상의 모든 자막 트랙을 반환한다.
    """
    try:
        results = await SubtitleService.fetch_subtitles(
            video_ids=request.video_ids,
            languages=request.languages,
            db=db,
        )
        return SubtitleFetchResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"자막 조회 실패: {str(e)}")
