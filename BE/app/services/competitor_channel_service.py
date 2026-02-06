import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.competitor_channel import CompetitorChannel
from app.schemas.competitor_channel import CompetitorChannelCreate

logger = logging.getLogger(__name__)


class CompetitorChannelService:
    """경쟁 유튜버 채널 관리 서비스"""

    @staticmethod
    async def add_competitor_channel(
        db: AsyncSession,
        channel_data: CompetitorChannelCreate,
        reference_channel_id: Optional[str] = None
    ) -> CompetitorChannel:
        """
        경쟁 채널 추가 (중복 체크)
        """
        # 중복 체크
        result = await db.execute(
            select(CompetitorChannel).where(
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
        
        logger.info(f"경쟁 채널 추가: {new_channel.title} ({new_channel.channel_id})")
        return new_channel

    @staticmethod
    async def get_all_competitor_channels(
        db: AsyncSession,
        reference_channel_id: Optional[str] = None
    ) -> List[CompetitorChannel]:
        """
        등록된 경쟁 채널 목록 조회
        """
        query = select(CompetitorChannel)
        
        if reference_channel_id:
            query = query.where(
                CompetitorChannel.reference_channel_id == reference_channel_id
            )
        
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
