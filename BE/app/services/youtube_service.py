import logging
from datetime import datetime, date
from typing import Any, Dict, List, Optional

import httpx
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
            "startDate": report_date.isoformat(),
            "endDate": report_date.isoformat(),
        }
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(YouTubeService.ANALYTICS_URL, params=params, headers=headers)
            # scope가 없으면 403이 반환될 수 있다.
            if resp.status_code in (401, 403):
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
            metrics="viewerPercentage,views,watchTimeMinutes",
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
            metrics="viewerPercentage,views,watchTimeMinutes",
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
