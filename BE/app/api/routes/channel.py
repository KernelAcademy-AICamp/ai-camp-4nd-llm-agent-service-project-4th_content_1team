from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from pydantic import BaseModel

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
    CompetitorChannelVideoResponse,
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
        
        # 수동 변환 (UUID → str)
        # recent_videos 변환
        videos_data = None
        if hasattr(channel, 'recent_videos') and channel.recent_videos:
            videos_data = [
                CompetitorChannelVideoResponse(
                    id=str(v.id),
                    video_id=v.video_id,
                    title=v.title,
                    description=v.description,
                    thumbnail_url=v.thumbnail_url,
                    published_at=v.published_at,
                    duration=v.duration,
                    view_count=v.view_count or 0,
                    like_count=v.like_count or 0,
                    comment_count=v.comment_count or 0,
                    analysis_summary=v.analysis_summary,
                    analysis_strengths=v.analysis_strengths,
                    analysis_weaknesses=v.analysis_weaknesses,
                    audience_reaction=v.audience_reaction,
                    analyzed_at=v.analyzed_at,
                )
                for v in channel.recent_videos
            ]

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
            recent_videos=videos_data,
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
            db, user_id=current_user.id, include_videos=True
        )

        # 수동 변환
        response_channels = []
        for ch in channels:
            # recent_videos relationship에서 영상 데이터 변환 (최대 3개)
            videos_data = None
            if hasattr(ch, 'recent_videos') and ch.recent_videos:
                videos_data = [
                    CompetitorChannelVideoResponse(
                        id=str(v.id),
                        video_id=v.video_id,
                        title=v.title,
                        description=v.description,
                        thumbnail_url=v.thumbnail_url,
                        published_at=v.published_at,
                        duration=v.duration,
                        view_count=v.view_count or 0,
                        like_count=v.like_count or 0,
                        comment_count=v.comment_count or 0,
                        analysis_summary=v.analysis_summary,
                        analysis_strengths=v.analysis_strengths,
                        analysis_weaknesses=v.analysis_weaknesses,
                        audience_reaction=v.audience_reaction,
                        analyzed_at=v.analyzed_at,
                    )
                    for v in ch.recent_videos[:3]  # 최대 3개만
                ]

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
                    recent_videos=videos_data,
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


@router.post("/competitor/update-videos")
async def update_competitor_videos(
    current_user: User = Depends(get_current_user),
):
    """
    경쟁 채널 최신 영상 업데이트 (수동 트리거)

    Celery 태스크를 트리거하여 모든 경쟁 채널의 최신 영상을 업데이트합니다.
    """
    try:
        from app.worker import task_update_all_competitor_videos

        # Celery 태스크 비동기 실행
        task = task_update_all_competitor_videos.delay()

        return {
            "success": True,
            "message": "경쟁 채널 최신 영상 업데이트가 시작되었습니다",
            "task_id": task.id
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"업데이트 시작 실패: {str(e)}"
        )


class FetchSubtitlesRequest(BaseModel):
    video_id: str


@router.post("/competitor/fetch-subtitles")
async def fetch_video_subtitles(
    request: FetchSubtitlesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    영상 자막 가져오기 (AI 분석용)

    캐시된 자막이 있으면 캐시 반환, 없으면 YouTube에서 가져와서 저장.
    """
    try:
        # 캐시 우선 확인 후 없으면 fetch
        result = await CompetitorChannelService.get_or_fetch_caption(
            db=db,
            youtube_video_id=request.video_id
        )

        cue_count = sum(len(t.get("cues", [])) for t in result.get("tracks", []))

        if result.get("status") != "success" or cue_count == 0:
            return {
                "success": False,
                "message": result.get("error") or "자막이 없거나 가져오기에 실패했습니다",
                "data": result
            }

        from_cache = result.get("from_cache", False)
        cache_msg = " (캐시)" if from_cache else ""

        return {
            "success": True,
            "message": f"자막 {cue_count}개 세그먼트 가져오기 성공{cache_msg}",
            "data": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"자막 가져오기 실패: {str(e)}"
        )
