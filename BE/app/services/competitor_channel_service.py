import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.competitor_channel import CompetitorChannel
from app.models.competitor_channel_video import CompetitorChannelVideo
from app.schemas.competitor_channel import CompetitorChannelCreate
from app.services.channel_service import ChannelService
from sqlalchemy import delete as sql_delete

logger = logging.getLogger(__name__)


class CompetitorChannelService:
    """경쟁 유튜버 채널 관리 서비스"""

    @staticmethod
    async def add_competitor_channel(
        db: AsyncSession,
        channel_data: CompetitorChannelCreate,
        user_id: UUID,
        reference_channel_id: Optional[str] = None,
        fetch_videos: bool = True
    ) -> CompetitorChannel:
        """
        경쟁 채널 추가 (사용자별 중복 체크)
        """
        # 같은 유저의 중복 체크
        result = await db.execute(
            select(CompetitorChannel).where(
                CompetitorChannel.user_id == user_id,
                CompetitorChannel.channel_id == channel_data.channel_id
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # 이미 있으면 정보 업데이트
            existing.title = channel_data.title
            existing.description = channel_data.description
            existing.custom_url = channel_data.custom_url
            existing.thumbnail_url = channel_data.thumbnail_url
            existing.subscriber_count = channel_data.subscriber_count
            existing.view_count = channel_data.view_count
            existing.video_count = channel_data.video_count
            existing.topic_categories = channel_data.topic_categories
            existing.keywords = channel_data.keywords
            existing.country = channel_data.country
            existing.published_at = channel_data.published_at
            existing.raw_data = channel_data.raw_data
            
            await db.commit()
            await db.refresh(existing)
            return existing
        
        # 새로 추가
        new_channel = CompetitorChannel(
            channel_id=channel_data.channel_id,
            user_id=user_id,
            title=channel_data.title,
            description=channel_data.description,
            custom_url=channel_data.custom_url,
            thumbnail_url=channel_data.thumbnail_url,
            subscriber_count=channel_data.subscriber_count,
            view_count=channel_data.view_count,
            video_count=channel_data.video_count,
            topic_categories=channel_data.topic_categories,
            keywords=channel_data.keywords,
            country=channel_data.country,
            published_at=channel_data.published_at,
            raw_data=channel_data.raw_data,
            reference_channel_id=reference_channel_id,
        )
        
        db.add(new_channel)
        await db.commit()
        await db.refresh(new_channel)
        
        # 최신 영상 3개 가져와서 별도 테이블에 저장 (테이블 생성 후 활성화)
        # TODO: alembic upgrade head 실행 후 fetch_videos=True로 변경
        # if fetch_videos:
        #     try:
        #         await CompetitorChannelService._save_recent_videos(
        #             db, new_channel.id, channel_data.channel_id
        #         )
        #         await db.commit()
        #     except Exception as e:
        #         logger.warning(f"최신 영상 저장 실패 (채널은 추가됨): {e}")
        #         await db.rollback()
        
        logger.info(f"경쟁 채널 추가: {new_channel.title} ({new_channel.channel_id})")
        return new_channel

    @staticmethod
    async def _save_recent_videos(
        db: AsyncSession,
        competitor_channel_id: UUID,
        youtube_channel_id: str
    ):
        """최신 영상 3개 저장"""
        try:
            # 기존 영상 삭제
            await db.execute(
                sql_delete(CompetitorChannelVideo).where(
                    CompetitorChannelVideo.competitor_channel_id == competitor_channel_id
                )
            )
            
            # 최신 영상 조회
            recent_videos = await ChannelService.get_channel_recent_videos(
                channel_id=youtube_channel_id,
                max_results=3
            )
            
            # DB에 저장
            for video_data in recent_videos:
                video = CompetitorChannelVideo(
                    competitor_channel_id=competitor_channel_id,
                    video_id=video_data.get("video_id"),
                    title=video_data.get("title"),
                    description=video_data.get("description"),
                    thumbnail_url=video_data.get("thumbnail_url"),
                    published_at=video_data.get("published_at"),
                    duration=video_data.get("duration"),
                    view_count=video_data.get("view_count", 0),
                    like_count=video_data.get("like_count", 0),
                    comment_count=video_data.get("comment_count", 0),
                )
                db.add(video)
            
            await db.flush()
            logger.info(f"최신 영상 {len(recent_videos)}개 저장 완료")
            
        except Exception as e:
            logger.error(f"최신 영상 저장 실패: {e}", exc_info=True)

    @staticmethod
    async def get_all_competitor_channels(
        db: AsyncSession,
        user_id: UUID,
        include_videos: bool = True
    ) -> List[CompetitorChannel]:
        """
        사용자의 등록된 경쟁 채널 목록 조회 (최신 영상 포함)
        """
        from sqlalchemy.orm import selectinload
        
        query = select(CompetitorChannel).where(
            CompetitorChannel.user_id == user_id
        )
        
        if include_videos:
            query = query.options(selectinload(CompetitorChannel.videos))
        
        query = query.order_by(CompetitorChannel.created_at.desc())
        
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def delete_competitor_channel(
        db: AsyncSession,
        competitor_id: UUID
    ) -> bool:
        """
        경쟁 채널 삭제
        """
        result = await db.execute(
            select(CompetitorChannel).where(CompetitorChannel.id == competitor_id)
        )
        channel = result.scalar_one_or_none()
        
        if not channel:
            raise HTTPException(status_code=404, detail="경쟁 채널을 찾을 수 없습니다")
        
        await db.delete(channel)
        await db.commit()
        
        logger.info(f"경쟁 채널 삭제: {channel.title} ({channel.channel_id})")
        return True
