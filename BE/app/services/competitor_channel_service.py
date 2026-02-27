import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

import httpx

from app.core.config import settings
from app.models.competitor_channel import CompetitorChannel
from app.models.competitor_channel_video import CompetitorRecentVideo, RecentVideoComment, RecentVideoCaption
from app.schemas.competitor_channel import CompetitorChannelCreate
from app.services.channel_service import ChannelService
from app.services.subtitle_service import SubtitleService
from sqlalchemy import delete as sql_delete
from app.services.keyword_extraction_service import extract_keywords_batch

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

            # 중복 제거 + 3개 제한
            seen_ids = set()
            unique_videos = []
            for v in recent_videos:
                vid = v.get("video_id")
                if vid and vid not in seen_ids:
                    seen_ids.add(vid)
                    unique_videos.append(v)
            recent_videos = unique_videos[:3]
            logger.info(f"YouTube API에서 {len(recent_videos)}개 영상 조회 (중복 제거 후)")

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

            # 각 영상의 자막 미리 가져오기 (AI 분석 속도 향상)
            for video, youtube_video_id in saved_videos:
                try:
                    caption_result = await CompetitorChannelService.get_or_fetch_caption(
                        db, youtube_video_id
                    )
                    cue_count = sum(len(t.get("cues", [])) for t in caption_result.get("tracks", []))
                    logger.info(f"자막 프리페치 완료: {youtube_video_id}, cues={cue_count}")
                except Exception as e:
                    logger.warning(f"자막 프리페치 실패 (분석 시 재시도): {youtube_video_id}: {e}")

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
    async def refresh_competitor_videos(
        db: AsyncSession,
        user_id: UUID,
    ) -> dict:
        """
        모든 경쟁 채널의 최신 영상을 확인하고 새 영상이 있으면 업데이트.

        1. 각 채널별로 YouTube에서 최신 1개 영상 ID를 조회
        2. DB에 저장된 영상 ID와 비교
        3. 새 영상이 있으면 3개 모두 다시 가져오기
        4. 새 영상이 없으면 스킵
        """
        channels = await CompetitorChannelService.get_all_competitor_channels(
            db, user_id, include_videos=True
        )

        updated = 0
        for channel in channels:
            try:
                # 최신 1개만 빠르게 조회하여 비교
                latest = await ChannelService.get_channel_recent_videos(
                    channel_id=channel.channel_id, max_results=1
                )
                if not latest:
                    continue

                latest_id = latest[0].get("video_id")
                existing_ids = [v.video_id for v in (channel.recent_videos or [])]

                if latest_id in existing_ids:
                    logger.info(f"새 영상 없음 (스킵): {channel.title}")
                    continue

                # 새 영상 발견 → 전체 3개 다시 가져오기
                logger.info(f"새 영상 발견! 갱신 시작: {channel.title}")
                await CompetitorChannelService._save_recent_videos(
                    db, channel.id, channel.channel_id
                )
                updated += 1

            except Exception as e:
                logger.warning(f"영상 갱신 실패 ({channel.title}): {e}")

        if updated > 0:
            await db.commit()

        logger.info(f"영상 갱신 완료: {updated}/{len(channels)} 채널 업데이트")
        return {
            "updated_channels": updated,
            "total_channels": len(channels),
        }

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

    @staticmethod
    async def analyze_recent_video(
        db: AsyncSession,
        youtube_video_id: str,
        user_id: UUID,
    ) -> dict:
        """
        경쟁 영상 AI 분석 (성공이유, 부족한점, 내 채널 적용 포인트)

        1. 영상 조회 + 캐시 확인
        2. 자막 텍스트 추출
        3. 유저 채널 페르소나 조회
        4. GPT-4o-mini로 분석
        5. 결과 저장 및 반환
        """
        # 1. CompetitorRecentVideo 조회
        result = await db.execute(
            select(CompetitorRecentVideo)
            .where(CompetitorRecentVideo.video_id == youtube_video_id)
            .limit(1)
        )
        video = result.scalar_one_or_none()

        if not video:
            raise HTTPException(status_code=404, detail="등록된 경쟁 영상을 찾을 수 없습니다")

        # 2. 캐시 확인 (이미 분석된 영상이면 즉시 반환)
        if video.analyzed_at and video.analysis_strengths and video.analysis_weaknesses and video.applicable_points:
            logger.info(f"캐시된 분석 결과 반환: {youtube_video_id}")
            return {
                "video_id": youtube_video_id,
                "analysis_strengths": video.analysis_strengths,
                "analysis_weaknesses": video.analysis_weaknesses,
                "applicable_points": video.applicable_points,
                "comment_insights": video.comment_insights or {"reactions": [], "needs": []},
                "analyzed_at": video.analyzed_at.isoformat(),
            }

        # 3. 자막 텍스트 추출
        caption_result = await CompetitorChannelService.get_or_fetch_caption(db, youtube_video_id)

        tracks = caption_result.get("tracks", [])
        cue_count = sum(len(t.get("cues", [])) for t in tracks)

        if cue_count == 0:
            raise HTTPException(status_code=400, detail="자막이 없는 영상은 AI 분석을 할 수 없습니다")

        # 자막 텍스트 합치기
        caption_text = ""
        for track in tracks:
            for cue in track.get("cues", []):
                caption_text += cue.get("text", "") + " "
        caption_text = caption_text.strip()

        # 자막 길이 제한
        max_chars = 12000
        if len(caption_text) > max_chars:
            caption_text = caption_text[:max_chars] + "..."

        # 4. 유저의 ChannelPersona 조회 (내 채널 컨텍스트)
        from app.models.channel_persona import ChannelPersona
        from app.models.youtube_channel import YouTubeChannel

        persona_context = ""
        try:
            yt_result = await db.execute(
                select(YouTubeChannel).where(YouTubeChannel.user_id == user_id)
            )
            my_channel = yt_result.scalar_one_or_none()

            if my_channel:
                persona_result = await db.execute(
                    select(ChannelPersona).where(ChannelPersona.channel_id == my_channel.channel_id)
                )
                persona = persona_result.scalar_one_or_none()

                if persona:
                    persona_context = f"""
[내 채널 정보]
- 채널 한줄 정의: {persona.one_liner or '없음'}
- 주요 주제: {', '.join(persona.main_topics) if persona.main_topics else '없음'}
- 콘텐츠 스타일: {persona.content_style or '없음'}
- 타겟 시청자: {persona.target_audience or '없음'}
- 차별화 포인트: {persona.differentiator or '없음'}
"""
        except Exception as e:
            logger.warning(f"페르소나 조회 실패 (분석은 계속): {e}")

        # 5. 댓글 데이터 추출
        comments_context = ""
        try:
            comments_result = await db.execute(
                select(RecentVideoComment)
                .where(RecentVideoComment.recent_video_id == video.id)
                .order_by(RecentVideoComment.likes.desc())
                .limit(10)
            )
            comments = list(comments_result.scalars().all())

            if comments:
                comment_lines = []
                for c in comments:
                    likes_str = f"(좋아요 {c.likes})" if c.likes else ""
                    comment_lines.append(f"- {c.text} {likes_str}")
                comments_text = "\n".join(comment_lines)
                comments_context = f"""
[시청자 댓글 (좋아요 순 상위 {len(comments)}개)]
{comments_text}
"""
                logger.info(f"댓글 {len(comments)}개 프롬프트에 포함")
        except Exception as e:
            logger.warning(f"댓글 조회 실패 (분석은 계속): {e}")

        # 6. LLM 호출
        api_key = settings.openai_api_key
        if not api_key:
            raise HTTPException(status_code=500, detail="OpenAI API 키가 설정되지 않았습니다.")

        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        llm = ChatOpenAI(model="gpt-4.1", api_key=api_key)

        prompt = f"""당신은 전문 유튜브 콘텐츠 분석가입니다. 경쟁 유튜버의 영상 자막과 시청자 댓글을 분석하여 4가지를 알려주세요.

분석 대상 영상 제목: {video.title}

[자막 트랜스크립트]
{caption_text}
{comments_context}{persona_context}
분석 지침:
1. "strengths" — 이 영상이 잘 된 이유 3~5개. 구체적 근거(자막 내용 인용)를 반드시 포함.
2. "weaknesses" — 이 영상에서 아쉬운 점 2~4개. "왜냐하면", "예를 들어" 등으로 구체적 이유를 반드시 포함.
3. "applicable_points" — 내 채널에 적용할 수 있는 구체적 액션 아이템 3~5개.
   {('내 채널 정보를 참고하여 맞춤형으로 제안해주세요.' if persona_context else '일반적인 유튜브 채널에 적용할 수 있도록 제안해주세요.')}
4. "comment_insights" — 댓글 분석 결과:
   - "reactions": 시청자들의 주요 반응 3~5개 (긍정/부정/요청 등 실제 댓글 내용 기반)
   - "needs": 시청자들이 원하는 콘텐츠/니즈 2~4개 (댓글에서 추출한 구체적 요구사항)
   {('댓글이 없으면 자막 내용에서 예상되는 시청자 반응과 니즈를 추론해주세요.' if not comments_context else '')}

작성 스타일:
- 한국어로 작성
- 쉽고 자연스러운 구어체 사용
- 구체적이고 실용적으로 작성 (추상적 표현 금지)
- 각 항목은 1~2문장으로 간결하게

출력 형식 (JSON만 출력, 다른 텍스트 없이):
{{
  "strengths": ["성공이유1", "성공이유2", ...],
  "weaknesses": ["부족한점1", "부족한점2", ...],
  "applicable_points": ["적용포인트1", "적용포인트2", ...],
  "comment_insights": {{
    "reactions": ["시청자 반응1", "시청자 반응2", ...],
    "needs": ["시청자 니즈1", "시청자 니즈2", ...]
  }}
}}"""

        try:
            res = llm.invoke([HumanMessage(content=prompt)])
            content = res.content.strip()
            content = content.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(content)
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"LLM 분석 파싱 실패: {e}")
            raise HTTPException(status_code=500, detail="영상 분석 중 오류가 발생했습니다.")

        strengths = parsed.get("strengths", [])
        weaknesses = parsed.get("weaknesses", [])
        applicable_points = parsed.get("applicable_points", [])
        comment_insights = parsed.get("comment_insights", {"reactions": [], "needs": []})

        # 결과 저장
        video.analysis_strengths = strengths
        video.analysis_weaknesses = weaknesses
        video.applicable_points = applicable_points
        video.comment_insights = comment_insights
        video.analyzed_at = datetime.utcnow()

        await db.commit()
        logger.info(f"영상 분석 완료: {youtube_video_id}")

        return {
            "video_id": youtube_video_id,
            "analysis_strengths": strengths,
            "analysis_weaknesses": weaknesses,
            "applicable_points": applicable_points,
            "comment_insights": comment_insights,
            "analyzed_at": video.analyzed_at.isoformat(),
        }

    @staticmethod
    async def _generate_applicable_points(
        db: AsyncSession,
        video: CompetitorRecentVideo,
        user_id: UUID,
    ) -> List[str]:
        """
        기존 분석 결과(strengths/weaknesses/comment_insights)를 기반으로
        내 채널 적용 포인트만 새로 생성하는 경량 LLM 호출.
        """
        from app.models.channel_persona import ChannelPersona
        from app.models.youtube_channel import YouTubeChannel

        # 페르소나 조회
        persona_context = "일반적인 유튜브 채널에 적용할 수 있도록 제안해주세요."
        try:
            yt_result = await db.execute(
                select(YouTubeChannel).where(YouTubeChannel.user_id == user_id)
            )
            my_channel = yt_result.scalar_one_or_none()
            if my_channel:
                persona_result = await db.execute(
                    select(ChannelPersona).where(ChannelPersona.channel_id == my_channel.channel_id)
                )
                persona = persona_result.scalar_one_or_none()
                if persona:
                    persona_context = f"""내 채널에 맞춤형으로 제안해주세요.
- 채널 정의: {persona.one_liner or '없음'}
- 주요 주제: {', '.join(persona.main_topics) if persona.main_topics else '없음'}
- 콘텐츠 스타일: {persona.content_style or '없음'}
- 타겟 시청자: {persona.target_audience or '없음'}
- 시청자 니즈: {persona.audience_needs or '없음'}
- 차별화 포인트: {persona.differentiator or '없음'}"""
        except Exception as e:
            logger.warning(f"페르소나 조회 실패: {e}")

        api_key = settings.openai_api_key
        if not api_key:
            return ["분석 결과를 참고하여 채널에 적용해보세요."]

        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        llm = ChatOpenAI(model="gpt-4.1", api_key=api_key)

        strengths_text = ", ".join(video.analysis_strengths or [])
        weaknesses_text = ", ".join(video.analysis_weaknesses or [])
        insights_text = json.dumps(video.comment_insights or {}, ensure_ascii=False)

        prompt = f"""경쟁 유튜버의 영상 분석 결과를 바탕으로, 내 채널에 적용할 수 있는 구체적 액션 아이템 3~5개를 제안해주세요.

[분석 대상 영상]
제목: {video.title}
성공 이유: {strengths_text}
부족한 점: {weaknesses_text}
시청자 반응: {insights_text}

[내 채널]
{persona_context}

작성 규칙:
- 한국어, 구어체, 구체적으로 작성
- 각 항목은 1~2문장

출력 형식 (JSON 문자열 배열만 출력, 다른 텍스트 없이):
["액션1", "액션2", "액션3"]"""

        try:
            res = llm.invoke([HumanMessage(content=prompt)])
            content = res.content.strip().replace("```json", "").replace("```", "").strip()
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return parsed
        except Exception as e:
            logger.error(f"적용 포인트 생성 실패: {e}")

        return ["경쟁 영상의 강점을 참고하여 채널에 적용해보세요."]

    @staticmethod
    async def auto_analyze_competitors(
        db: AsyncSession,
        user_id: UUID,
    ) -> dict:
        """
        자동 경쟁자 분석 파이프라인

        1. 최신 영상 갱신 (새 영상 있으면 업데이트)
        2. 미분석 영상 자동 분석
           - 다른 유저가 같은 영상을 이미 분석했으면 → 공유 결과 재사용 + applicable_points만 새로 생성
           - 아니면 → 전체 분석 (자막 + LLM)
        """
        # 1. 최신 영상 갱신
        try:
            refresh_result = await CompetitorChannelService.refresh_competitor_videos(db, user_id)
        except Exception as e:
            logger.warning(f"영상 갱신 실패 (분석은 계속): {e}")
            refresh_result = {"updated_channels": 0, "total_channels": 0}

        # 2. 전체 채널 + 영상 조회
        channels = await CompetitorChannelService.get_all_competitor_channels(
            db, user_id, include_videos=True
        )

        analyzed_count = 0
        reused_count = 0
        skipped_count = 0

        for ch in channels:
            for video in (ch.recent_videos or []):
                # 이미 분석 완료된 영상은 스킵
                if video.analyzed_at is not None:
                    skipped_count += 1
                    continue

                try:
                    # 다른 유저의 같은 YouTube 영상에서 분석 결과 조회
                    shared_result = await db.execute(
                        select(CompetitorRecentVideo).where(
                            and_(
                                CompetitorRecentVideo.video_id == video.video_id,
                                CompetitorRecentVideo.id != video.id,
                                CompetitorRecentVideo.analyzed_at.isnot(None),
                            )
                        ).limit(1)
                    )
                    shared_video = shared_result.scalar_one_or_none()

                    if shared_video:
                        # 공유 분석 결과 복사 (범용 필드)
                        video.analysis_strengths = shared_video.analysis_strengths
                        video.analysis_weaknesses = shared_video.analysis_weaknesses
                        video.comment_insights = shared_video.comment_insights

                        # 내 채널 적용 포인트만 새로 생성
                        points = await CompetitorChannelService._generate_applicable_points(
                            db, video, user_id
                        )
                        video.applicable_points = points
                        video.analyzed_at = datetime.utcnow()
                        await db.commit()

                        reused_count += 1
                        logger.info(f"공유 분석 재사용 + 적용포인트 생성: {video.video_id}")
                    else:
                        # 전체 분석 수행 (자막 fetch + 전체 LLM)
                        await CompetitorChannelService.analyze_recent_video(
                            db, video.video_id, user_id
                        )
                        analyzed_count += 1

                except Exception as e:
                    logger.warning(f"자동 분석 실패 ({video.video_id}): {e}")
                    continue

        total = analyzed_count + reused_count
        logger.info(
            f"자동 분석 완료: 새 분석 {analyzed_count}건, 재사용 {reused_count}건, "
            f"스킵 {skipped_count}건"
        )

        return {
            "refresh": refresh_result,
            "analyzed": analyzed_count,
            "reused": reused_count,
            "skipped": skipped_count,
        }

    @staticmethod
    async def generate_competitor_topics(
        db: AsyncSession,
        user_id: UUID,
    ) -> List[dict]:
        """
        경쟁자 기반 주제 추천 (4개)

        경쟁 채널 데이터 + 분석 결과를 종합하여 LLM으로 4개 주제를 추천합니다.
        결과는 ChannelTopic 테이블에 저장됩니다.
        """
        from app.models.channel_persona import ChannelPersona
        from app.models.youtube_channel import YouTubeChannel
        from app.models.content_topic import ChannelTopic

        # 1. 유저의 YouTube 채널 조회
        yt_result = await db.execute(
            select(YouTubeChannel).where(YouTubeChannel.user_id == user_id)
        )
        my_channel = yt_result.scalar_one_or_none()
        if not my_channel:
            raise HTTPException(status_code=404, detail="연결된 YouTube 채널이 없습니다")

        channel_id = my_channel.channel_id

        # 2. 경쟁 채널 + 최신 영상 조회
        channels = await CompetitorChannelService.get_all_competitor_channels(
            db, user_id, include_videos=True
        )

        if not channels:
            raise HTTPException(status_code=400, detail="등록된 경쟁 채널이 없습니다")

        # 3. 분석 완료된 영상만 필터
        competitor_data_lines = []
        for ch in channels:
            ch_info = f"채널명: {ch.title}, 구독자: {(ch.subscriber_count or 0):,}명"
            if ch.content_style:
                ch_info += f", 콘텐츠스타일: {ch.content_style}"
            if ch.strengths:
                ch_info += f", 강점: {', '.join(ch.strengths)}"
            competitor_data_lines.append(ch_info)

            analyzed_videos = [
                v for v in (ch.recent_videos or [])
                if v.analyzed_at is not None
            ]
            for v in analyzed_videos:
                v_info = f"  - 영상: {v.title} (조회수: {(v.view_count or 0):,})"
                if v.analysis_strengths:
                    v_info += f"\n    성공이유: {', '.join(v.analysis_strengths[:3])}"
                if v.analysis_weaknesses:
                    v_info += f"\n    부족한점: {', '.join(v.analysis_weaknesses[:3])}"
                if v.applicable_points:
                    v_info += f"\n    적용포인트: {', '.join(v.applicable_points[:3])}"
                if v.comment_insights:
                    needs = v.comment_insights.get("needs", [])
                    if needs:
                        v_info += f"\n    시청자니즈: {', '.join(needs[:3])}"
                competitor_data_lines.append(v_info)

        competitor_context = "\n".join(competitor_data_lines)

        if not competitor_context.strip():
            raise HTTPException(status_code=400, detail="분석된 경쟁 영상이 없습니다. 먼저 경쟁 영상을 분석해주세요.")

        # 4. 유저 채널 페르소나 조회
        persona_context = ""
        try:
            persona_result = await db.execute(
                select(ChannelPersona).where(ChannelPersona.channel_id == channel_id)
            )
            persona = persona_result.scalar_one_or_none()
            if persona:
                lines = ["[내 채널 페르소나]"]
                if persona.persona_summary:
                    lines.append(f"- 채널 요약: {persona.persona_summary}")
                if persona.one_liner:
                    lines.append(f"- 한줄 정의: {persona.one_liner}")
                if persona.main_topics:
                    lines.append(f"- 주요 주제: {', '.join(persona.main_topics)}")
                if persona.content_style:
                    lines.append(f"- 콘텐츠 스타일: {persona.content_style}")
                if persona.differentiator:
                    lines.append(f"- 차별화 포인트: {persona.differentiator}")

                lines.append("")
                lines.append("[타겟 시청자 정보]")
                if persona.target_audience:
                    lines.append(f"- 타겟 시청자층: {persona.target_audience}")
                if persona.audience_needs:
                    lines.append(f"- 시청자가 원하는 것: {persona.audience_needs}")

                lines.append("")
                lines.append("[채널 성공 공식]")
                if persona.hit_topics:
                    lines.append(f"- 잘 되는 주제: {', '.join(persona.hit_topics)}")
                if persona.title_patterns:
                    lines.append(f"- 잘 먹히는 제목 패턴: {', '.join(persona.title_patterns)}")
                if persona.optimal_duration:
                    lines.append(f"- 최적 영상 길이: {persona.optimal_duration}")

                if persona.growth_opportunities:
                    lines.append("")
                    lines.append(f"[성장 기회 영역]: {', '.join(persona.growth_opportunities)}")

                persona_context = "\n".join(lines)
        except Exception as e:
            logger.warning(f"페르소나 조회 실패 (분석은 계속): {e}")

        # 5. LLM 프롬프트 구성
        api_key = settings.anthropic_api_key
        if not api_key:
            raise HTTPException(status_code=500, detail="Anthropic API 키가 설정되지 않았습니다.")

        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import HumanMessage

        llm = ChatAnthropic(model="claude-sonnet-4-5", api_key=api_key)

        prompt = f"""당신은 유튜브 콘텐츠 전략 분석가입니다.

아래 경쟁 유튜버 채널 데이터와 내 채널 페르소나를 종합 분석하여, 내 채널에 최적화된 콘텐츠 주제 4개를 추천해주세요.

[경쟁 채널 데이터]
{competitor_context}

{persona_context}

핵심 분석 과정:
1. 경쟁자들의 제목 패턴 추출 (숫자형, 질문형, 비교형 등)
2. 콘텐츠 유형 분류 (튜토리얼, 뉴스해석, 실전빌드 등)
3. 경쟁자들이 다루지 않는 콘텐츠 공백(gap) 발견
4. 경쟁자 강점 반영 + 부족한점/남은 각도 보완 가능한 주제 4개 추천

중요 — 반드시 내 채널 페르소나를 기반으로 추천하세요:
- 내 채널의 정체성(한줄 정의, 콘텐츠 스타일, 차별화 포인트)에 맞는 주제여야 합니다.
- 내 타겟 시청자층이 실제로 궁금해할 주제, 시청자가 원하는 것(니즈)을 해결하는 주제를 추천하세요.
- 내 채널에서 잘 되는 주제와 제목 패턴을 참고하여, 제목을 내 채널 톤에 맞게 작성하세요.
- 성장 기회 영역이 있다면 해당 방향의 주제도 고려하세요.

각 주제는 반드시 다음을 포함:
- title: 내 채널 스타일과 제목 패턴에 맞는 구체적이고 클릭하고 싶은 영상 제목
- recommendation_reason: 아래 3가지를 모두 포함하여 3~5문장으로 작성
  (1) 왜 이 주제가 경쟁자 분석 관점에서 유망한지
  (2) 내 타겟 시청자층이 왜 이 주제에 관심을 가질지
  (3) 내 채널에서 이 주제를 어떤 방향/톤/스타일로 영상을 만들면 좋을지 구체적 제안
- content_angles: 내 채널 관점에서 이 주제를 다룰 수 있는 구체적 관점 3개
- urgency: "urgent" 또는 "normal" 또는 "evergreen"
- search_keywords: 이 주제와 관련된 검색 키워드 3~5개
- trend_basis: 이 주제가 유망한 근거 1문장

작성 스타일:
- 한국어로 작성
- 쉽고 자연스러운 구어체 사용
- 구체적이고 실용적으로 작성 (추상적 표현 금지)

⚠️ 필수 규칙: 반드시 정확히 4개의 주제를 출력해야 합니다. 3개나 5개가 아닌 4개.

출력 형식 (JSON 배열만 출력, 다른 텍스트 없이, 반드시 4개):
[
  {{
    "title": "첫 번째 영상 제목",
    "recommendation_reason": "추천 이유",
    "content_angles": ["관점1", "관점2", "관점3"],
    "urgency": "normal",
    "search_keywords": ["키워드1", "키워드2", "키워드3"],
    "trend_basis": "유망 근거"
  }},
  {{
    "title": "두 번째 영상 제목",
    "recommendation_reason": "추천 이유",
    "content_angles": ["관점1", "관점2", "관점3"],
    "urgency": "normal",
    "search_keywords": ["키워드1", "키워드2", "키워드3"],
    "trend_basis": "유망 근거"
  }},
  {{
    "title": "세 번째 영상 제목",
    "recommendation_reason": "추천 이유",
    "content_angles": ["관점1", "관점2", "관점3"],
    "urgency": "urgent",
    "search_keywords": ["키워드1", "키워드2", "키워드3"],
    "trend_basis": "유망 근거"
  }},
  {{
    "title": "네 번째 영상 제목",
    "recommendation_reason": "추천 이유",
    "content_angles": ["관점1", "관점2", "관점3"],
    "urgency": "evergreen",
    "search_keywords": ["키워드1", "키워드2", "키워드3"],
    "trend_basis": "유망 근거"
  }}
]"""

        try:
            res = llm.invoke([HumanMessage(content=prompt)])
            content = res.content.strip()
            content = content.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(content)
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"경쟁자 주제 추천 LLM 파싱 실패: {e}")
            raise HTTPException(status_code=500, detail="경쟁자 분석 기반 주제 추천 중 오류가 발생했습니다.")

        if not isinstance(parsed, list) or len(parsed) == 0:
            raise HTTPException(status_code=500, detail="주제 추천 결과가 올바르지 않습니다.")

        # 4개 미만이면 재시도 (최대 1회)
        if len(parsed) < 4:
            logger.warning(f"경쟁자 주제 추천이 {len(parsed)}개만 반환됨, 재시도...")
            try:
                res2 = llm.invoke([HumanMessage(content=prompt)])
                content2 = res2.content.strip()
                content2 = content2.replace("```json", "").replace("```", "").strip()
                parsed2 = json.loads(content2)
                if isinstance(parsed2, list) and len(parsed2) > len(parsed):
                    parsed = parsed2
                    logger.info(f"재시도 후 {len(parsed)}개 반환됨")
            except Exception as e:
                logger.warning(f"재시도 실패 (기존 결과 사용): {e}")

        # 5.5. 키워드 에이전트로 search_keywords 품질 향상
        titles = [item.get("title", "") for item in parsed[:4]]
        keyword_results = await extract_keywords_batch(titles)
        for item, new_keywords in zip(parsed[:4], keyword_results):
            if new_keywords:
                item["search_keywords"] = new_keywords

        # 6. 기존 competitor_analysis 주제 삭제
        await db.execute(
            sql_delete(ChannelTopic).where(
                and_(
                    ChannelTopic.channel_id == channel_id,
                    ChannelTopic.based_on_topic.like("competitor_analysis%"),
                )
            )
        )
        await db.flush()

        # 7. 새 ChannelTopic 4개 생성
        created_topics = []
        for idx, item in enumerate(parsed[:4]):
            topic = ChannelTopic(
                channel_id=channel_id,
                rank=idx + 1,
                display_status="shown",
                title=item.get("title", "제목 없음"),
                based_on_topic="competitor_analysis",
                trend_basis=item.get("trend_basis"),
                recommendation_reason=item.get("recommendation_reason"),
                urgency=item.get("urgency", "normal"),
                search_keywords=item.get("search_keywords", []),
                content_angles=item.get("content_angles", []),
                status="recommended",
                expires_at=datetime.utcnow() + timedelta(days=7),
            )
            db.add(topic)
            created_topics.append(topic)

        await db.commit()

        # refresh to get generated IDs
        for t in created_topics:
            await db.refresh(t)

        logger.info(f"경쟁자 기반 주제 추천 {len(created_topics)}개 생성 완료")

        return [
            {
                "title": t.title,
                "recommendation_reason": t.recommendation_reason,
                "content_angles": t.content_angles or [],
                "urgency": t.urgency,
                "search_keywords": t.search_keywords or [],
                "trend_basis": t.trend_basis,
            }
            for t in created_topics
        ]
