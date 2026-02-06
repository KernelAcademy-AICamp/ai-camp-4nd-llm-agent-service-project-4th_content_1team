from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.youtube_channel import YouTubeChannel
from app.schemas.channel import (
    ChannelSearchRequest,
    ChannelSearchResponse,
    ChannelSearchResult,
)
from app.schemas.competitor_channel import (
    CompetitorChannelCreate,
    CompetitorChannelResponse,
    CompetitorChannelListResponse,
)
from app.services.channel_service import ChannelService
from app.services.competitor_channel_service import CompetitorChannelService
from sqlalchemy import select

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


@router.post("/competitor/add", response_model=CompetitorChannelResponse)
async def add_competitor_channel(
    request: CompetitorChannelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    경쟁 채널 추가
    """
    try:
        # 내 채널 ID 조회
        stmt = select(YouTubeChannel).where(YouTubeChannel.user_id == current_user.id)
        result = await db.execute(stmt)
        my_channel = result.scalar_one_or_none()
        
        reference_channel_id = my_channel.channel_id if my_channel else None
        
        channel = await CompetitorChannelService.add_competitor_channel(
            db=db,
            channel_data=request,
            user_id=current_user.id,
            reference_channel_id=reference_channel_id
        )
        
        # 수동 변환 (UUID → str, videos 제외)
        return CompetitorChannelResponse(
            id=str(channel.id),
            channel_id=channel.channel_id,
            title=channel.title,
            description=channel.description,
            custom_url=channel.custom_url,
            thumbnail_url=channel.thumbnail_url,
            subscriber_count=channel.subscriber_count,
            view_count=channel.view_count,
            video_count=channel.video_count,
            strengths=channel.strengths,
            channel_personality=channel.channel_personality,
            target_audience=channel.target_audience,
            content_style=channel.content_style,
            videos=None,  # 추가 시에는 videos 안 보냄
            created_at=channel.created_at,
            updated_at=channel.updated_at,
            analyzed_at=channel.analyzed_at,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"경쟁 채널 추가 실패: {str(e)}"
        )


@router.get("/competitor/list", response_model=CompetitorChannelListResponse)
async def get_competitor_channels(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    사용자의 등록된 경쟁 채널 목록 조회
    """
    try:
        channels = await CompetitorChannelService.get_all_competitor_channels(
            db, user_id=current_user.id, include_videos=False  # 테이블 생성 전까지 비활성화
        )
        
        # 수동 변환 (videos 접근하지 않음)
        response_channels = []
        for ch in channels:
            response_channels.append(
                CompetitorChannelResponse(
                    id=str(ch.id),
                    channel_id=ch.channel_id,
                    title=ch.title,
                    description=ch.description,
                    custom_url=ch.custom_url,
                    thumbnail_url=ch.thumbnail_url,
                    subscriber_count=ch.subscriber_count,
                    view_count=ch.view_count,
                    video_count=ch.video_count,
                    strengths=ch.strengths,
                    channel_personality=ch.channel_personality,
                    target_audience=ch.target_audience,
                    content_style=ch.content_style,
                    videos=None,  # 테이블 생성 전까지 None
                    created_at=ch.created_at,
                    updated_at=ch.updated_at,
                    analyzed_at=ch.analyzed_at,
                )
            )
        
        return CompetitorChannelListResponse(
            total=len(channels),
            channels=response_channels
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"경쟁 채널 목록 조회 실패: {str(e)}"
        )


@router.delete("/competitor/{competitor_id}")
async def delete_competitor_channel(
    competitor_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    경쟁 채널 삭제
    """
    try:
        await CompetitorChannelService.delete_competitor_channel(db, competitor_id)
        return {"success": True, "message": "경쟁 채널이 삭제되었습니다"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"경쟁 채널 삭제 실패: {str(e)}"
        )
