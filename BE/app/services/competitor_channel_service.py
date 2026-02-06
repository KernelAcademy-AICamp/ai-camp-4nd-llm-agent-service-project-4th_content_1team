import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

import httpx

from app.core.config import settings
from app.models.competitor_channel import CompetitorChannel
from app.models.competitor_channel_video import CompetitorRecentVideo, RecentVideoComment, RecentVideoCaption
from app.schemas.competitor_channel import CompetitorChannelCreate
from app.services.channel_service import ChannelService
from app.services.subtitle_service import SubtitleService
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

            # relationship을 포함해서 다시 로드
            from sqlalchemy.orm import selectinload
            result = await db.execute(
                select(CompetitorChannel)
                .where(CompetitorChannel.id == existing.id)
                .options(selectinload(CompetitorChannel.recent_videos))
            )
            return result.scalar_one()
        
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

        # 최신 영상 3개 가져와서 별도 테이블에 저장
        if fetch_videos:
            try:
                await CompetitorChannelService._save_recent_videos(
                    db, new_channel.id, channel_data.channel_id
                )
                await db.commit()
                logger.info(f"최신 영상 저장 완료")
            except Exception as e:
                logger.warning(f"최신 영상 저장 실패 (채널은 추가됨): {e}")

        # relationship을 포함해서 다시 로드
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(CompetitorChannel)
            .where(CompetitorChannel.id == new_channel.id)
            .options(selectinload(CompetitorChannel.recent_videos))
        )
        new_channel = result.scalar_one()

        logger.info(f"경쟁 채널 추가: {new_channel.title} ({new_channel.channel_id})")
        return new_channel

    @staticmethod
    async def _save_recent_videos(
        db: AsyncSession,
        competitor_channel_id: UUID,
        youtube_channel_id: str
    ):
        """최신 영상 3개 저장 및 각 영상의 댓글 저장"""
        try:
            # 기존 영상 삭제 (cascade로 댓글도 삭제됨)
            await db.execute(
                sql_delete(CompetitorRecentVideo).where(
                    CompetitorRecentVideo.competitor_channel_id == competitor_channel_id
                )
            )
            await db.flush()  # 삭제 즉시 반영

            # 최신 영상 조회 (최대 3개)
            recent_videos = await ChannelService.get_channel_recent_videos(
                channel_id=youtube_channel_id,
                max_results=3
            )

            # 안전장치: 3개 초과 시 잘라내기
            recent_videos = recent_videos[:3]
            logger.info(f"YouTube API에서 {len(recent_videos)}개 영상 조회")

            saved_videos = []

            # DB에 저장
            for video_data in recent_videos:
                # published_at 문자열을 datetime으로 변환
                published_at = video_data.get("published_at")
                if published_at and isinstance(published_at, str):
                    try:
                        published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                    except ValueError:
                        published_at = None

                video = CompetitorRecentVideo(
                    competitor_channel_id=competitor_channel_id,
                    video_id=video_data.get("video_id"),
                    title=video_data.get("title"),
                    description=video_data.get("description"),
                    thumbnail_url=video_data.get("thumbnail_url"),
                    published_at=published_at,
                    duration=video_data.get("duration"),
                    view_count=video_data.get("view_count", 0),
                    like_count=video_data.get("like_count", 0),
                    comment_count=video_data.get("comment_count", 0),
                )
                db.add(video)
                saved_videos.append((video, video_data.get("video_id")))

            await db.flush()
            logger.info(f"최신 영상 {len(recent_videos)}개 저장 완료")

            # 각 영상의 댓글 저장 (좋아요 순 상위 10개)
            for video, youtube_video_id in saved_videos:
                try:
                    logger.info(f"댓글 저장 시작: video_id={video.id}, youtube_id={youtube_video_id}")
                    await CompetitorChannelService._save_video_comments(
                        db, video.id, youtube_video_id, max_results=10
                    )
                except Exception as e:
                    logger.error(f"영상 댓글 저장 실패 ({youtube_video_id}): {e}", exc_info=True)

            await db.flush()
            logger.info("댓글 저장 완료 (flush)")

        except Exception as e:
            logger.error(f"최신 영상 저장 실패: {e}", exc_info=True)
            raise

    @staticmethod
    async def _save_video_comments(
        db: AsyncSession,
        recent_video_id: UUID,
        youtube_video_id: str,
        max_results: int = 10
    ):
        """영상 댓글 저장 (좋아요 순 상위 N개)"""
        try:
            # YouTube API로 댓글 가져오기
            comments_data = await CompetitorChannelService._fetch_youtube_comments(
                youtube_video_id, max_results=max_results * 2  # 필터링 위해 더 가져옴
            )

            if not comments_data:
                logger.info(f"댓글 없음: {youtube_video_id}")
                return

            # 좋아요 순 정렬 후 상위 N개 선택
            sorted_comments = sorted(
                comments_data,
                key=lambda x: -(x.get("likes", 0) or 0)
            )[:max_results]

            # DB에 저장
            for comment_data in sorted_comments:
                published_at = comment_data.get("published_at")
                if published_at and isinstance(published_at, str):
                    try:
                        published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                    except ValueError:
                        published_at = None

                comment = RecentVideoComment(
                    recent_video_id=recent_video_id,
                    comment_id=comment_data.get("comment_id"),
                    text=comment_data.get("text", ""),
                    author_name=comment_data.get("author_name"),
                    author_thumbnail=comment_data.get("author_thumbnail"),
                    likes=comment_data.get("likes", 0),
                    published_at=published_at,
                )
                db.add(comment)

            logger.info(f"댓글 {len(sorted_comments)}개 저장: {youtube_video_id}")

        except Exception as e:
            logger.error(f"댓글 저장 실패 ({youtube_video_id}): {e}")

    @staticmethod
    async def _fetch_youtube_comments(
        video_id: str,
        max_results: int = 20
    ) -> List[dict]:
        """YouTube API로 댓글 가져오기"""
        BASE_URL = "https://www.googleapis.com/youtube/v3"
        api_key = settings.youtube_api_key

        params = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": min(max_results, 100),
            "order": "relevance",
            "key": api_key,
        }

        try:
            logger.info(f"YouTube 댓글 API 호출: {video_id}")
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(f"{BASE_URL}/commentThreads", params=params)
                logger.info(f"YouTube 댓글 API 응답: status={resp.status_code}, video_id={video_id}")

                if resp.status_code == 403:
                    error_detail = resp.text[:200] if resp.text else "No detail"
                    logger.warning(f"YouTube API 403 에러 ({video_id}): {error_detail}")
                    return []

                if resp.status_code == 404:
                    logger.info(f"댓글 없음 또는 비활성화: {video_id}")
                    return []

                resp.raise_for_status()
                data = resp.json()

                items = data.get("items", [])
                logger.info(f"YouTube API에서 {len(items)}개 댓글 항목 수신: {video_id}")

                comments = []
                for item in items:
                    snippet = item.get("snippet", {})
                    top_comment = snippet.get("topLevelComment", {})
                    comment_snippet = top_comment.get("snippet", {})

                    comments.append({
                        "comment_id": top_comment.get("id"),
                        "text": comment_snippet.get("textDisplay", ""),
                        "author_name": comment_snippet.get("authorDisplayName"),
                        "author_thumbnail": comment_snippet.get("authorProfileImageUrl"),
                        "likes": comment_snippet.get("likeCount", 0),
                        "published_at": comment_snippet.get("publishedAt"),
                    })

                logger.info(f"파싱된 댓글 {len(comments)}개: {video_id}")
                return comments

        except httpx.TimeoutException:
            logger.error(f"YouTube 댓글 API timeout: {video_id}")
            return []
        except Exception as e:
            logger.error(f"YouTube 댓글 API error ({video_id}): {e}")
            return []

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
            query = query.options(selectinload(CompetitorChannel.recent_videos))
        
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

    @staticmethod
    async def get_or_fetch_caption(
        db: AsyncSession,
        youtube_video_id: str
    ) -> dict:
        """
        자막 가져오기 (캐시 우선, 없으면 YouTube에서 fetch)

        1. RecentVideoCaption 테이블에서 캐시 확인
        2. 캐시 없으면 SubtitleService로 YouTube에서 가져오기
        3. 가져온 자막을 DB에 저장
        """
        # 1. CompetitorRecentVideo 조회
        result = await db.execute(
            select(CompetitorRecentVideo)
            .where(CompetitorRecentVideo.video_id == youtube_video_id)
            .limit(1)
        )
        recent_video = result.scalar_one_or_none()

        if not recent_video:
            logger.warning(f"CompetitorRecentVideo 없음: {youtube_video_id}")
            return {
                "video_id": youtube_video_id,
                "status": "failed",
                "error": "등록된 경쟁 유튜버의 최신 영상이 아닙니다",
                "tracks": [],
                "no_captions": True,
                "from_cache": False,
            }

        # 2. RecentVideoCaption에서 캐시 확인
        result = await db.execute(
            select(RecentVideoCaption)
            .where(RecentVideoCaption.recent_video_id == recent_video.id)
        )
        cached_caption = result.scalar_one_or_none()

        if cached_caption and cached_caption.segments_json:
            segments = cached_caption.segments_json
            # 자막 데이터가 있는지 확인
            tracks = segments.get("tracks", [])
            cue_count = sum(len(t.get("cues", [])) for t in tracks)

            if cue_count > 0:
                logger.info(f"캐시된 자막 반환: {youtube_video_id}, cues={cue_count}")
                return {
                    "video_id": youtube_video_id,
                    "status": "success",
                    "source": segments.get("source", "cache"),
                    "tracks": tracks,
                    "no_captions": False,
                    "from_cache": True,
                }

        # 3. 캐시 없음 → YouTube에서 가져오기
        logger.info(f"캐시 없음, YouTube에서 자막 가져오기: {youtube_video_id}")

        results = await SubtitleService.fetch_subtitles(
            video_ids=[youtube_video_id],
            languages=["ko", "en"],
            db=None,  # 기존 VideoCaption 테이블에 저장하지 않음
        )

        if not results:
            return {
                "video_id": youtube_video_id,
                "status": "failed",
                "error": "자막을 가져올 수 없습니다",
                "tracks": [],
                "no_captions": True,
                "from_cache": False,
            }

        fetch_result = results[0]
        cue_count = sum(len(t.get("cues", [])) for t in fetch_result.get("tracks", []))

        # 4. 성공하면 RecentVideoCaption에 저장
        if fetch_result.get("status") == "success" and cue_count > 0:
            segments_data = {
                "source": fetch_result.get("source", "yt-dlp"),
                "tracks": fetch_result.get("tracks", []),
                "no_captions": False,
            }

            # 기존 캐시가 있으면 업데이트, 없으면 생성
            if cached_caption:
                cached_caption.segments_json = segments_data
                logger.info(f"자막 캐시 업데이트: {youtube_video_id}")
            else:
                new_caption = RecentVideoCaption(
                    recent_video_id=recent_video.id,
                    segments_json=segments_data,
                )
                db.add(new_caption)
                logger.info(f"자막 캐시 생성: {youtube_video_id}")

            await db.commit()

        fetch_result["from_cache"] = False
        return fetch_result
