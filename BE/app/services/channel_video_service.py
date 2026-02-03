"""
채널 영상 수집 서비스

사용자 채널의 영상 목록과 성과 통계를 수집합니다.
YouTube Data API를 사용하여 영상 메타데이터와 통계를 가져옵니다.
"""
from datetime import date
from typing import List, Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel_video import YTChannelVideo, YTVideoStats
from app.core.config import settings


# YouTube Data API 기본 URL
YT_API_BASE = "https://www.googleapis.com/youtube/v3"


async def get_channel_uploads_playlist_id(
    channel_id: str,
    api_key: str,
) -> Optional[str]:
    """
    채널의 uploads playlist ID 조회.

    YouTube에서 채널의 모든 영상은 "uploads" 플레이리스트에 저장됩니다.
    채널 ID가 UC로 시작하면, UU로 바꾸면 uploads playlist ID가 됩니다.
    """
    # 간단한 변환: UC -> UU
    if channel_id.startswith("UC"):
        return "UU" + channel_id[2:]

    # API로 조회 (UC로 시작하지 않는 경우)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{YT_API_BASE}/channels",
            params={
                "key": api_key,
                "id": channel_id,
                "part": "contentDetails",
            },
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        items = data.get("items", [])
        if not items:
            return None

        return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


async def fetch_playlist_videos(
    playlist_id: str,
    api_key: str,
    max_results: int = 50,
) -> List[dict]:
    """
    플레이리스트에서 영상 목록 조회.

    Returns:
        [{"video_id": "...", "title": "...", "published_at": "..."}, ...]
    """
    videos = []
    page_token = None

    async with httpx.AsyncClient() as client:
        while len(videos) < max_results:
            params = {
                "key": api_key,
                "playlistId": playlist_id,
                "part": "snippet",
                "maxResults": min(50, max_results - len(videos)),
            }
            if page_token:
                params["pageToken"] = page_token

            resp = await client.get(f"{YT_API_BASE}/playlistItems", params=params)
            if resp.status_code != 200:
                break

            data = resp.json()
            for item in data.get("items", []):
                snippet = item["snippet"]
                videos.append({
                    "video_id": snippet["resourceId"]["videoId"],
                    "title": snippet["title"],
                    "description": snippet.get("description", ""),
                    "published_at": snippet.get("publishedAt"),
                    "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                })

            page_token = data.get("nextPageToken")
            if not page_token:
                break

    return videos


async def fetch_video_details(
    video_ids: List[str],
    api_key: str,
) -> List[dict]:
    """
    영상 상세 정보 조회 (duration, tags, 통계).

    Returns:
        [{"video_id": "...", "duration_seconds": 600, "tags": [...],
          "view_count": 1000, "like_count": 50, "comment_count": 10}, ...]
    """
    if not video_ids:
        return []

    results = []

    # YouTube API는 한 번에 최대 50개까지만 조회 가능
    async with httpx.AsyncClient() as client:
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i+50]

            resp = await client.get(
                f"{YT_API_BASE}/videos",
                params={
                    "key": api_key,
                    "id": ",".join(batch),
                    "part": "contentDetails,statistics,snippet",
                },
            )
            if resp.status_code != 200:
                continue

            data = resp.json()
            for item in data.get("items", []):
                vid = item["id"]
                content = item.get("contentDetails", {})
                stats = item.get("statistics", {})
                snippet = item.get("snippet", {})

                # ISO 8601 duration을 초로 변환 (PT1H2M3S -> 3723)
                duration_str = content.get("duration", "PT0S")
                duration_seconds = _parse_iso_duration(duration_str)

                results.append({
                    "video_id": vid,
                    "duration_seconds": duration_seconds,
                    "tags": snippet.get("tags", []),
                    "view_count": int(stats.get("viewCount", 0)),
                    "like_count": int(stats.get("likeCount", 0)),
                    "comment_count": int(stats.get("commentCount", 0)),
                })

    return results


def _parse_iso_duration(duration: str) -> int:
    """ISO 8601 duration을 초로 변환. PT1H2M3S -> 3723"""
    import re

    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if not match:
        return 0

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    return hours * 3600 + minutes * 60 + seconds


async def sync_channel_videos(
    db: AsyncSession,
    channel_id: str,
    max_results: int = 50,
) -> List[YTChannelVideo]:
    """
    채널의 최근 영상을 수집하여 DB에 저장.

    Args:
        db: 데이터베이스 세션
        channel_id: YouTube 채널 ID
        max_results: 수집할 최대 영상 수 (기본 50)

    Returns:
        저장된 YTChannelVideo 목록
    """
    api_key = settings.youtube_api_key
    if not api_key:
        raise ValueError("YOUTUBE_API_KEY 환경변수가 설정되지 않았습니다.")

    # 1. uploads playlist ID 조회
    playlist_id = await get_channel_uploads_playlist_id(channel_id, api_key)
    if not playlist_id:
        return []

    # 2. 플레이리스트에서 영상 목록 조회
    videos_basic = await fetch_playlist_videos(playlist_id, api_key, max_results)
    if not videos_basic:
        return []

    # 3. 영상 상세 정보 조회
    video_ids = [v["video_id"] for v in videos_basic]
    videos_detail = await fetch_video_details(video_ids, api_key)
    detail_map = {v["video_id"]: v for v in videos_detail}

    # 4. DB에 저장 (upsert) - Race condition 처리 포함
    from sqlalchemy.exc import IntegrityError

    saved_videos = []
    for basic in videos_basic:
        vid = basic["video_id"]
        detail = detail_map.get(vid, {})

        # 기존 레코드 확인
        stmt = select(YTChannelVideo).where(
            YTChannelVideo.channel_id == channel_id,
            YTChannelVideo.video_id == vid,
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # 업데이트
            existing.title = basic["title"]
            existing.description = basic["description"]
            existing.thumbnail_url = basic.get("thumbnail_url")
            existing.duration_seconds = detail.get("duration_seconds")
            existing.tags = detail.get("tags")
            saved_videos.append(existing)
        else:
            # 새로 생성
            from datetime import datetime
            published_at = None
            if basic.get("published_at"):
                try:
                    published_at = datetime.fromisoformat(
                        basic["published_at"].replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            video = YTChannelVideo(
                channel_id=channel_id,
                video_id=vid,
                title=basic["title"],
                description=basic["description"],
                published_at=published_at,
                duration_seconds=detail.get("duration_seconds"),
                tags=detail.get("tags"),
                thumbnail_url=basic.get("thumbnail_url"),
            )
            db.add(video)
            saved_videos.append(video)

    try:
        await db.commit()
    except IntegrityError:
        # Race condition: 다른 요청이 먼저 저장함 → 기존 데이터 사용
        await db.rollback()
        return await get_channel_videos(db, channel_id)

    # 5. 통계도 함께 저장
    await sync_video_stats(db, saved_videos, detail_map)

    return saved_videos


async def sync_video_stats(
    db: AsyncSession,
    videos: List[YTChannelVideo],
    detail_map: dict,
) -> List[YTVideoStats]:
    """
    영상별 통계 저장 (오늘 날짜 기준).

    Args:
        db: 데이터베이스 세션
        videos: YTChannelVideo 목록
        detail_map: {video_id: {view_count, like_count, comment_count}}
    """
    today = date.today()
    saved_stats = []

    for video in videos:
        detail = detail_map.get(video.video_id, {})
        if not detail:
            continue

        # 기존 레코드 확인
        stmt = select(YTVideoStats).where(
            YTVideoStats.video_id == video.id,
            YTVideoStats.date == today,
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # 업데이트
            existing.view_count = detail.get("view_count")
            existing.like_count = detail.get("like_count")
            existing.comment_count = detail.get("comment_count")
            saved_stats.append(existing)
        else:
            # 새로 생성
            stat = YTVideoStats(
                video_id=video.id,
                date=today,
                view_count=detail.get("view_count"),
                like_count=detail.get("like_count"),
                comment_count=detail.get("comment_count"),
            )
            db.add(stat)
            saved_stats.append(stat)

    await db.commit()
    return saved_stats


async def get_channel_videos(
    db: AsyncSession,
    channel_id: str,
    limit: int = 50,
) -> List[YTChannelVideo]:
    """
    DB에서 채널 영상 조회.
    """
    stmt = (
        select(YTChannelVideo)
        .where(YTChannelVideo.channel_id == channel_id)
        .order_by(YTChannelVideo.published_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_video_stats(
    db: AsyncSession,
    video_id: UUID,
) -> List[YTVideoStats]:
    """
    DB에서 영상 통계 조회 (날짜순).
    """
    stmt = (
        select(YTVideoStats)
        .where(YTVideoStats.video_id == video_id)
        .order_by(YTVideoStats.date.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
