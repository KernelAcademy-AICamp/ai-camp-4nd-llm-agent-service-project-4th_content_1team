import logging
import math
from datetime import datetime, date, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.youtube_channel import (
    YouTubeChannel,
    YTChannelStatsDaily,
    YTChannelTopic,
    YTAudienceDaily,
    YTGeoDaily,
)

logger = logging.getLogger(__name__)


class YouTubeService:
    """YouTube Data/Analytics API 연동 서비스."""

    BASE_URL = "https://www.googleapis.com/youtube/v3"
    ANALYTICS_URL = "https://youtubeanalytics.googleapis.com/v2/reports"

    # ---------- Public API ----------
    @staticmethod
    async def sync_user_channel(
        db: AsyncSession,
        user_id,
        access_token: str,
        report_date: Optional[date] = None,
    ) -> YouTubeChannel:
        """
        mine=true 채널을 조회해 저장/업데이트하고 당일 통계를 기록한다.
        """
        report_date = report_date or date.today()

        channel_resp = await YouTubeService._fetch_my_channel(access_token)
        items = channel_resp.get("items", [])
        if not items:
            raise ValueError("YouTube channel not found for the authenticated user")

        parsed = YouTubeService.parse_channel_item(items[0])
        channel = await YouTubeService._upsert_channel(db, user_id, parsed)
        await YouTubeService._upsert_daily_stats(db, channel.channel_id, parsed, report_date)
        await YouTubeService._sync_topics(db, channel.channel_id, parsed)

        # Analytics 보고서는 scope가 없거나 권한이 없을 수 있으므로 실패를 삼킨다.
        await YouTubeService._safe_record_analytics(db, channel.channel_id, access_token, report_date)

        await db.commit()
        await db.refresh(channel)
        return channel

    @staticmethod
    def parse_channel_item(item: Dict[str, Any]) -> Dict[str, Any]:
        """채널 API 응답을 저장용 dict로 변환 (테스트 가능)."""
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {}) or {}
        branding = item.get("brandingSettings", {}) or {}
        topic_details = item.get("topicDetails", {}) or {}

        channel_id = item.get("id")
        channel_keywords = branding.get("channel", {}).get("keywords")
        # keywords가 list일 수도 있으므로 문자열로 안전히 변환
        if isinstance(channel_keywords, list):
            keywords = ",".join(channel_keywords)
        else:
            keywords = channel_keywords

        def _to_int(value):
            try:
                return int(value) if value is not None else None
            except (TypeError, ValueError):
                return None

        return {
            "channel_id": channel_id,
            "title": snippet.get("title"),
            "description": snippet.get("description"),
            "country": snippet.get("country"),
            "keywords": keywords,
            "raw_channel_json": item,
            "stats": {
                "subscriber_count": _to_int(statistics.get("subscriberCount")),
                "view_count": _to_int(statistics.get("viewCount")),
                "video_count": _to_int(statistics.get("videoCount")),
                "comment_count": _to_int(statistics.get("commentCount")),
                "raw_stats_json": statistics,
            },
            "topics": topic_details.get("topicCategories") or [],
        }

    # ---------- Internal helpers ----------
    @staticmethod
    async def _fetch_my_channel(access_token: str) -> Dict[str, Any]:
        params = {
            "part": "snippet,statistics,topicDetails,brandingSettings",
            "mine": "true",
        }
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{YouTubeService.BASE_URL}/channels", params=params, headers=headers)
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    async def _upsert_channel(db: AsyncSession, user_id, parsed: Dict[str, Any]) -> YouTubeChannel:
        result = await db.execute(
            select(YouTubeChannel).where(YouTubeChannel.channel_id == parsed["channel_id"])
        )
        channel = result.scalar_one_or_none()

        if channel:
            channel.title = parsed.get("title")
            channel.description = parsed.get("description")
            channel.country = parsed.get("country")
            channel.keywords = parsed.get("keywords")
            channel.raw_channel_json = parsed.get("raw_channel_json")
            channel.updated_at = datetime.utcnow()
        else:
            channel = YouTubeChannel(
                channel_id=parsed["channel_id"],
                user_id=user_id,
                title=parsed.get("title"),
                description=parsed.get("description"),
                country=parsed.get("country"),
                keywords=parsed.get("keywords"),
                raw_channel_json=parsed.get("raw_channel_json"),
            )
            db.add(channel)

        await db.flush()
        return channel

    @staticmethod
    async def _upsert_daily_stats(
        db: AsyncSession,
        channel_id: str,
        parsed: Dict[str, Any],
        report_date: date,
    ) -> None:
        stats = parsed.get("stats") or {}
        result = await db.execute(
            select(YTChannelStatsDaily).where(
                YTChannelStatsDaily.channel_id == channel_id,
                YTChannelStatsDaily.date == report_date,
            )
        )
        row = result.scalar_one_or_none()
        if row:
            row.subscriber_count = stats.get("subscriber_count")
            row.view_count = stats.get("view_count")
            row.video_count = stats.get("video_count")
            row.comment_count = stats.get("comment_count")
            row.raw_stats_json = stats.get("raw_stats_json")
        else:
            db.add(
                YTChannelStatsDaily(
                    channel_id=channel_id,
                    date=report_date,
                    subscriber_count=stats.get("subscriber_count"),
                    view_count=stats.get("view_count"),
                    video_count=stats.get("video_count"),
                    comment_count=stats.get("comment_count"),
                    raw_stats_json=stats.get("raw_stats_json"),
                )
            )
        await db.flush()

    @staticmethod
    async def _sync_topics(db: AsyncSession, channel_id: str, parsed: Dict[str, Any]) -> None:
        topics: List[str] = parsed.get("topics") or []
        new_topics = set(topics)

        result = await db.execute(select(YTChannelTopic).where(YTChannelTopic.channel_id == channel_id))
        existing_rows = result.scalars().all()
        existing_topics = {row.topic_category_url for row in existing_rows}

        to_delete = existing_topics - new_topics
        if to_delete:
            await db.execute(
                delete(YTChannelTopic).where(
                    YTChannelTopic.channel_id == channel_id, YTChannelTopic.topic_category_url.in_(to_delete)
                )
            )

        for topic in new_topics - existing_topics:
            db.add(YTChannelTopic(channel_id=channel_id, topic_category_url=topic))

        await db.flush()

    @staticmethod
    async def _safe_record_analytics(
        db: AsyncSession,
        channel_id: str,
        access_token: str,
        report_date: date,
    ) -> None:
        try:
            await YouTubeService._record_audience(db, channel_id, access_token, report_date)
            await YouTubeService._record_geo(db, channel_id, access_token, report_date)
        except httpx.HTTPStatusError as exc:
            # 권한 부족(401/403) 등은 로그인 성공을 막지 않는다.
            logger.warning("YouTube Analytics fetch skipped: %s", exc)
        except Exception as exc:  # pragma: no cover - 방어적 로깅
            logger.warning("YouTube Analytics processing error: %s", exc)

    @staticmethod
    async def _fetch_analytics_report(
        access_token: str,
        channel_id: str,
        dimensions: str,
        metrics: str,
        report_date: date,
    ) -> Optional[Dict[str, Any]]:
        params = {
            "ids": f"channel=={channel_id}",
            "dimensions": dimensions,
            "metrics": metrics,
            "startDate": (report_date - timedelta(days=30)).isoformat(),
            "endDate": report_date.isoformat(),
        }
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(YouTubeService.ANALYTICS_URL, params=params, headers=headers)
            # scope가 없거나 권한/데이터 부족 시 400/401/403이 반환될 수 있다.
            if resp.status_code in (400, 401, 403):
                logger.info(
                    "YouTube Analytics skipped (status=%s, dims=%s, metrics=%s)",
                    resp.status_code,
                    dimensions,
                    metrics,
                )
                return None
            resp.raise_for_status()
            data = resp.json()
            logger.info(
                "YouTube Analytics fetched (dims=%s, metrics=%s, rows=%s)",
                dimensions,
                metrics,
                len(data.get("rows", [])) if isinstance(data, dict) else "n/a",
            )
            return data

    @staticmethod
    async def _record_audience(
        db: AsyncSession,
        channel_id: str,
        access_token: str,
        report_date: date,
    ) -> None:
        report = await YouTubeService._fetch_analytics_report(
            access_token,
            channel_id,
            dimensions="ageGroup,gender",
            metrics="viewerPercentage",
            report_date=report_date,
        )
        if not report or not report.get("rows"):
            return

        headers = [h.get("name") for h in report.get("columnHeaders", [])]
        for row in report["rows"]:
            row_dict = dict(zip(headers, row))
            await YouTubeService._upsert_audience_row(db, channel_id, report_date, row_dict)
        await db.flush()

    @staticmethod
    async def _upsert_audience_row(
        db: AsyncSession,
        channel_id: str,
        report_date: date,
        row: Dict[str, Any],
    ) -> None:
        def _to_float(val):
            try:
                return float(val) if val is not None else None
            except (TypeError, ValueError):
                return None

        def _to_int(val):
            try:
                return int(val) if val is not None else None
            except (TypeError, ValueError):
                return None

        age_group = row.get("ageGroup")
        gender = row.get("gender")

        result = await db.execute(
            select(YTAudienceDaily).where(
                YTAudienceDaily.channel_id == channel_id,
                YTAudienceDaily.date == report_date,
                YTAudienceDaily.age_group == age_group,
                YTAudienceDaily.gender == gender,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.viewer_percentage = _to_float(row.get("viewerPercentage"))
            existing.views = _to_int(row.get("views"))
            existing.watch_time_minutes = _to_float(row.get("watchTimeMinutes"))
            existing.raw_report_json = row
        else:
            db.add(
                YTAudienceDaily(
                    channel_id=channel_id,
                    date=report_date,
                    age_group=age_group,
                    gender=gender,
                    viewer_percentage=_to_float(row.get("viewerPercentage")),
                    views=_to_int(row.get("views")),
                    watch_time_minutes=_to_float(row.get("watchTimeMinutes")),
                    raw_report_json=row,
                )
            )

    @staticmethod
    async def _record_geo(
        db: AsyncSession,
        channel_id: str,
        access_token: str,
        report_date: date,
    ) -> None:
        report = await YouTubeService._fetch_analytics_report(
            access_token,
            channel_id,
            dimensions="country",
            metrics="views,estimatedMinutesWatched",
            report_date=report_date,
        )
        if not report or not report.get("rows"):
            return

        headers = [h.get("name") for h in report.get("columnHeaders", [])]
        for row in report["rows"]:
            row_dict = dict(zip(headers, row))
            await YouTubeService._upsert_geo_row(db, channel_id, report_date, row_dict)
        await db.flush()

    @staticmethod
    async def _upsert_geo_row(
        db: AsyncSession,
        channel_id: str,
        report_date: date,
        row: Dict[str, Any],
    ) -> None:
        def _to_float(val):
            try:
                return float(val) if val is not None else None
            except (TypeError, ValueError):
                return None

        def _to_int(val):
            try:
                return int(val) if val is not None else None
            except (TypeError, ValueError):
                return None

        country = row.get("country")

        result = await db.execute(
            select(YTGeoDaily).where(
                YTGeoDaily.channel_id == channel_id,
                YTGeoDaily.date == report_date,
                YTGeoDaily.country == country,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.viewer_percentage = _to_float(row.get("viewerPercentage"))
            existing.views = _to_int(row.get("views"))
            existing.watch_time_minutes = _to_float(row.get("watchTimeMinutes"))
            existing.raw_report_json = row
        else:
            db.add(
                YTGeoDaily(
                    channel_id=channel_id,
                    date=report_date,
                    country=country,
                    viewer_percentage=_to_float(row.get("viewerPercentage")),
                    views=_to_int(row.get("views")),
                    watch_time_minutes=_to_float(row.get("watchTimeMinutes")),
                    raw_report_json=row,
                )
            )

    # ==================== YouTube 비디오 트렌드 검색 기능 ====================

    @staticmethod
    async def search_popular_videos(
        keywords: str,
        title: Optional[str] = None,
        max_results: int = 10,
        api_key: str = None
    ) -> List[Dict[str, Any]]:
        """
        트렌드 인기도 기준 YouTube 비디오 검색.
        
        Args:
            keywords: 검색 키워드 (필수)
            title: 제목 필터 (선택)
            max_results: 반환할 결과 수 (기본 10)
            api_key: YouTube Data API 키
            
        Returns:
            트렌드 인기도순으로 정렬된 비디오 리스트
            
        알고리즘:
            popularity_score = (views_per_day × recency_weight) + engagement_score
            - views_per_day: 일일 조회수 (viewCount / days_since_upload)
            - recency_weight: 신선도 가중치 (30일 이내 최대 2배)
            - engagement_score: 참여도 (likeCount × 0.1 + commentCount × 0.05)
        """
        # 1. 검색 쿼리 구성
        query = YouTubeService._build_query(keywords, title)
        logger.info(f"YouTube search query: {query}")
        
        # 2. search.list로 video_ids 수집 (50개)
        video_ids = await YouTubeService._search_video_ids(
            query, api_key, fetch_count=50
        )
        
        if not video_ids:
            logger.warning(f"No videos found for query: {query}")
            return []
        
        logger.info(f"Found {len(video_ids)} video IDs")
        
        # 3. videos.list로 상세 정보 조회
        video_details = await YouTubeService._get_video_details(
            video_ids, api_key
        )
        
        logger.info(f"Retrieved details for {len(video_details)} videos")
        
        # 4. 트렌드 점수 계산
        for video in video_details:
            score, days = YouTubeService._calculate_popularity_score(video)
            video["popularity_score"] = score
            video["days_since_upload"] = days
        
        # 5. 정렬 및 상위 N개 반환
        sorted_videos = sorted(
            video_details,
            key=lambda x: x.get("popularity_score", 0),
            reverse=True
        )
        
        result = sorted_videos[:max_results]
        logger.info(f"Returning top {len(result)} videos")
        
        return result

    @staticmethod
    def _calculate_popularity_score(
        video: Dict[str, Any]
    ) -> tuple[float, int]:
        """
        트렌드 인기도 점수 계산.
        
        공식:
            popularity_score = (views_per_day × recency_weight) + engagement_score
            
        where:
            - views_per_day = viewCount / days_since_upload
            - recency_weight = 1 + max(0, (30 - days_since_upload) / 30)
            - engagement_score = likeCount × 0.1 + commentCount × 0.05
        
        Returns:
            (popularity_score, days_since_upload)
        """
        # 업로드 날짜 파싱
        published_at_str = video.get("snippet", {}).get("publishedAt")
        if not published_at_str:
            return (0.0, 0)
        
        try:
            published_at = datetime.fromisoformat(
                published_at_str.replace("Z", "+00:00")
            )
        except (ValueError, AttributeError):
            logger.warning(f"Invalid publishedAt format: {published_at_str}")
            return (0.0, 0)
        
        now = datetime.now(timezone.utc)
        
        # 경과 일수 (최소 1일)
        days_since_upload = max((now - published_at).days, 1)
        
        # 통계 추출
        stats = video.get("statistics", {})
        try:
            view_count = int(stats.get("viewCount", 0))
            like_count = int(stats.get("likeCount", 0))
            comment_count = int(stats.get("commentCount", 0))
        except (ValueError, TypeError):
            logger.warning(f"Invalid statistics for video: {video.get('id')}")
            return (0.0, days_since_upload)
        
        # 1. 일일 조회수
        views_per_day = view_count / days_since_upload

        # 2. 신선도 가중치 (점진적 페널티 적용)
        # - 30일 이내: 2.0 → 1.0 (보너스)
        # - 31~90일: 1.0 → 0.5 (약한 페널티)
        # - 91일+: 0.5 → 0.2 (강한 페널티, 최소 0.2)
        if days_since_upload <= 30:
            recency_weight = 2.0 - (days_since_upload / 30)  # 2.0 → 1.0
        elif days_since_upload <= 90:
            recency_weight = 1.0 - ((days_since_upload - 30) / 120)  # 1.0 → 0.5
        else:
            recency_weight = max(0.2, 0.5 - ((days_since_upload - 90) / 365))  # 최소 0.2

        # 3. 참여도 점수 (비율 기반으로 정규화)
        # 조회수 대비 참여율로 계산하여 오래된 영상의 누적 이점 제거
        if view_count > 0:
            like_ratio = like_count / view_count
            comment_ratio = comment_count / view_count
            # 참여율에 조회수 스케일 적용 (로그 스케일로 큰 영상 이점 완화)
            view_scale = math.log10(max(view_count, 10))  # 최소 1
            engagement_score = (like_ratio * 1000 + comment_ratio * 500) * view_scale
        else:
            engagement_score = 0

        # 4. 최종 점수
        popularity_score = (views_per_day * recency_weight) + engagement_score
        
        return (popularity_score, days_since_upload)

    @staticmethod
    def _build_query(keywords: str, title: Optional[str]) -> str:
        """
        검색 쿼리 생성 (최적화된 전략).
        
        전략: intitle: 연산자 활용
        - keywords: 넓은 범위로 검색 (컨텐츠 전체)
        - title: intitle: 연산자로 제목 필터링 (관련성 향상)
        
        예시:
            - keywords="python tutorial", title="beginner"
            - 결과: "python tutorial intitle:beginner"
            - 의미: "python tutorial" 포함 & 제목에 "beginner" 포함
        """
        if not title:
            return keywords
        
        # intitle: 연산자로 제목 필터링
        # 공백 포함 시 따옴표로 감싸기
        if " " in title:
            return f'{keywords} intitle:"{title}"'
        else:
            return f"{keywords} intitle:{title}"

    @staticmethod
    async def _search_video_ids(
        query: str,
        api_key: str,
        fetch_count: int = 50
    ) -> List[str]:
        """
        search.list API로 video IDs 수집.
        
        Args:
            query: 검색 쿼리
            api_key: YouTube Data API 키
            fetch_count: 가져올 비디오 수 (최대 50)
            
        Returns:
            비디오 ID 리스트
        """
        params = {
            "part": "id",
            "q": query,
            "type": "video",
            "maxResults": min(fetch_count, 50),  # YouTube API 최대 50개
            "key": api_key
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{YouTubeService.BASE_URL}/search",
                    params=params
                )
                
                # 할당량 초과 처리
                if resp.status_code == 403:
                    error_data = resp.json()
                    error_reason = error_data.get("error", {}).get("errors", [{}])[0].get("reason", "")
                    if "quotaExceeded" in error_reason:
                        raise HTTPException(
                            status_code=429,
                            detail="YouTube API 일일 할당량 초과"
                        )
                
                resp.raise_for_status()
                data = resp.json()
                
                return [
                    item["id"]["videoId"]
                    for item in data.get("items", [])
                    if item.get("id", {}).get("videoId")
                ]
        except httpx.TimeoutException:
            logger.error(f"YouTube search API timeout for query: {query}")
            raise HTTPException(
                status_code=504,
                detail="YouTube API 요청 시간 초과"
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"YouTube search API error: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"YouTube 검색 중 오류 발생: {str(e)}"
            )

    @staticmethod
    async def _get_video_details(
        video_ids: List[str],
        api_key: str
    ) -> List[Dict[str, Any]]:
        """
        videos.list API로 비디오 상세 정보 조회.
        
        Args:
            video_ids: 비디오 ID 리스트
            api_key: YouTube Data API 키
            
        Returns:
            비디오 상세 정보 리스트
        """
        if not video_ids:
            return []
        
        params = {
            "part": "snippet,statistics",
            "id": ",".join(video_ids),
            "key": api_key
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{YouTubeService.BASE_URL}/videos",
                    params=params
                )
                resp.raise_for_status()
                data = resp.json()
                
                return data.get("items", [])
        except httpx.TimeoutException:
            logger.error("YouTube videos API timeout")
            raise HTTPException(
                status_code=504,
                detail="YouTube API 요청 시간 초과"
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"YouTube videos API error: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"비디오 정보 조회 중 오류 발생: {str(e)}"
            )
