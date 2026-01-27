from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Tuple

import httpx

from app.core.config import settings


YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"


class YouTubeServiceError(Exception):
    """Custom exception for YouTube service errors."""


class YouTubeService:
    """Service layer for querying YouTube and computing popularity."""

    @staticmethod
    def _build_query(title: str, keywords: Iterable[str] | None) -> str:
        base = title.strip()
        extra = " ".join(kw.strip() for kw in (keywords or []) if kw and kw.strip())
        return f"{base} {extra}".strip()

    @staticmethod
    async def _search_video_ids(
        query: str,
        max_results: int = 50,
        days_window: int = 30,
    ) -> List[str]:
        """Call YouTube Search API to get candidate video IDs."""
        if not settings.youtube_api_key:
            raise YouTubeServiceError("YouTube API key is not configured.")

        now = datetime.now(timezone.utc)
        published_after = (now - timedelta(days=days_window)).isoformat()

        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_results,
            "order": "relevance",
            "publishedAfter": published_after,
            "key": settings.youtube_api_key,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{YOUTUBE_API_BASE_URL}/search", params=params)

        if resp.status_code != 200:
            raise YouTubeServiceError(
                f"YouTube search API error: {resp.status_code} {resp.text}"
            )

        data = resp.json()
        items = data.get("items", [])
        video_ids: List[str] = []
        for item in items:
            video_id = (
                item.get("id", {})
                .get("videoId")
            )
            if video_id:
                video_ids.append(video_id)

        return video_ids

    @staticmethod
    async def _fetch_videos_details(
        video_ids: List[str],
    ) -> List[dict]:
        """Fetch statistics and snippet details for given video IDs."""
        if not video_ids:
            return []

        if not settings.youtube_api_key:
            raise YouTubeServiceError("YouTube API key is not configured.")

        params = {
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(video_ids),
            "key": settings.youtube_api_key,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{YOUTUBE_API_BASE_URL}/videos", params=params)

        if resp.status_code != 200:
            raise YouTubeServiceError(
                f"YouTube videos API error: {resp.status_code} {resp.text}"
            )

        data = resp.json()
        return data.get("items", [])

    @staticmethod
    def _compute_popularity_metrics(
        video_item: dict,
        like_weight: float = 50.0,
    ) -> Tuple[float, float, float, datetime]:
        """Compute views/day, likes/day and combined popularity score."""
        snippet = video_item.get("snippet", {})
        statistics = video_item.get("statistics", {})

        published_at_str = snippet.get("publishedAt")
        # YouTube returns RFC3339 (e.g. 2024-01-01T00:00:00Z)
        published_at = datetime.fromisoformat(
            published_at_str.replace("Z", "+00:00")
        ) if published_at_str else datetime.now(timezone.utc)

        now = datetime.now(timezone.utc)
        days = (now - published_at).total_seconds() / 86400.0
        if days <= 0:
            days = 1.0

        view_count = float(statistics.get("viewCount", 0) or 0)
        like_count = float(statistics.get("likeCount", 0) or 0)

        views_per_day = view_count / days
        likes_per_day = like_count / days
        popularity_score = views_per_day + like_weight * likes_per_day

        return views_per_day, likes_per_day, popularity_score, published_at

    @classmethod
    async def get_popular_videos(
        cls,
        title: str,
        keywords: Iterable[str] | None = None,
        days_window: int = 30,
        max_candidates: int = 50,
        top_k: int = 10,
    ) -> List[dict]:
        """High-level function to get top-K popular videos for given query."""
        query = cls._build_query(title, keywords)
        if not query:
            return []

        video_ids = await cls._search_video_ids(
            query=query,
            max_results=max_candidates,
            days_window=days_window,
        )

        details = await cls._fetch_videos_details(video_ids)
        enriched: List[dict] = []

        for item in details:
            video_id = item.get("id")
            snippet = item.get("snippet", {})
            statistics = item.get("statistics", {})

            views_per_day, likes_per_day, popularity_score, published_at = (
                cls._compute_popularity_metrics(item)
            )

            thumbnails = snippet.get("thumbnails", {}) or {}
            # Pick a reasonable default thumbnail (high → medium → default)
            thumb_url = (
                thumbnails.get("high", {}) or
                thumbnails.get("medium", {}) or
                thumbnails.get("default", {}) or
                {}
            ).get("url")

            enriched.append(
                {
                    "video_id": video_id,
                    "title": snippet.get("title", ""),
                    "channel_title": snippet.get("channelTitle", ""),
                    "published_at": published_at,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "thumbnail_url": thumb_url,
                    "view_count": int(statistics.get("viewCount", 0) or 0),
                    "like_count": int(statistics.get("likeCount", 0) or 0),
                    "views_per_day": views_per_day,
                    "likes_per_day": likes_per_day,
                    "popularity_score": popularity_score,
                }
            )

        # Sort by popularity score descending and take top_k
        enriched.sort(key=lambda x: x["popularity_score"], reverse=True)
        return enriched[:top_k]

