from fastapi import APIRouter, HTTPException

from app.schemas.channel import (
    ChannelSearchRequest,
    ChannelSearchResponse,
    ChannelSearchResult,
)
from app.services.channel_service import ChannelService

router = APIRouter(prefix="/api/v1/channels", tags=["Channels"])


@router.post("/search", response_model=ChannelSearchResponse)
async def search_channels(request: ChannelSearchRequest):
    """
    YouTube 채널 검색
    
    - 채널 이름으로 검색
    - 채널 URL에서 ID 추출하여 조회
    - @핸들로 조회
    """
    try:
        channels_data = await ChannelService.search_channels(
            query=request.query,
            max_results=10
        )
        
        channels = [
            ChannelSearchResult(**ch)
            for ch in channels_data
        ]
        
        return ChannelSearchResponse(
            total_results=len(channels),
            channels=channels
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"채널 검색 실패: {str(e)}"
        )
