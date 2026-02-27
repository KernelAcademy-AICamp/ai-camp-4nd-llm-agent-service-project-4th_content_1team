"""
YouTube Fetcher Node - 유튜브 영상 검색 에이전트
주제와 관련된 인기 유튜브 영상을 검색하여 경쟁사 분석 재료를 제공합니다.
"""

import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.youtube_service import YouTubeService
from app.core.db import get_db

logger = logging.getLogger(__name__)


def yt_fetcher_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    YouTube에서 주제 관련 인기 영상을 검색하는 노드

    Input (from state):
        - topic: 주제
        - content_brief: Planner가 생성한 검색 쿼리

    Output (to state):
        - youtube_data: 검색된 영상 리스트 (제목, URL, 조회수, 채널 등)
                        + related_videos: UI 표시용 관련 영상 2개
    """
    logger.info("=" * 60)
    logger.info("[YT Fetcher] 노드 시작")

    # 1. 입력 데이터 추출
    topic = state.get("topic", "")
    content_brief = state.get("content_brief", {})
    search_queries = content_brief.get("search_queries", [])  # = youtube_keywords from planner

    logger.info(f"[YT Fetcher] 주제: {topic}")
    logger.info(f"[YT Fetcher] 플래너 youtube_keywords (search_queries): {search_queries}")

    # 검색 쿼리가 없으면 주제를 그대로 사용
    if not search_queries:
        search_queries = [topic]
        logger.warning(f"[YT Fetcher] youtube_keywords 없음 → 주제로 대체: {topic}")

    # 2. 경쟁사 분석용 YouTube 검색 (기존)
    videos = []
    try:
        logger.info(f"[YT Fetcher] 경쟁사 분석용 검색 시작 (쿼리: {search_queries[:2]})")
        videos = _search_youtube_videos(search_queries[:2])
        logger.info(f"[YT Fetcher] 경쟁사 분석용 검색 완료: {len(videos)}개 영상")
    except Exception as e:
        logger.error(f"[YT Fetcher] 경쟁사 분석용 검색 실패: {e}", exc_info=True)

    # 3. UI 표시용 관련 영상 검색 (신규)
    related_videos = []
    try:
        logger.info(f"[YT Fetcher] 관련 영상 검색 시작 (키워드: {search_queries[:2]})")
        related_videos = _search_related_videos_for_display(search_queries[:2])
        logger.info(f"[YT Fetcher] 관련 영상 검색 완료: {len(related_videos)}개")
        for i, v in enumerate(related_videos):
            logger.info(
                f"[YT Fetcher] 관련 영상 [{i+1}] type={v.get('search_type')} | "
                f"'{v.get('title', '')[:40]}' | "
                f"키워드='{v.get('search_keyword')}' | "
                f"조회수={v.get('view_count')} | "
                f"velocity={v.get('view_velocity')}"
            )
    except Exception as e:
        logger.error(f"[YT Fetcher] 관련 영상 검색 실패: {e}", exc_info=True)

    logger.info("[YT Fetcher] 노드 완료")
    logger.info("=" * 60)

    return {
        "youtube_data": {
            "videos": videos,
            "related_videos": related_videos,
            "search_queries_used": search_queries[:2],
        }
    }


def _search_related_videos_for_display(keywords: List[str]) -> List[Dict]:
    """
    플래너 youtube_keywords로 UI 표시용 관련 영상 2개를 검색합니다.

    - keywords[0] → relevance 순 검색 → 첫 번째 유효 영상 (search_type="relevance")
    - keywords[1] → relevance 검색 후 view_velocity 정렬 → 1위 (search_type="popular")

    Returns:
        최대 2개의 영상 dict (search_type 필드 포함)
    """
    import os
    from datetime import datetime, timezone

    api_key = os.getenv("YOUTUBE_API_KEY")
    results: List[Dict] = []
    seen_ids: set = set()

    logger.info(f"[관련 영상] API 키 존재: {bool(api_key)}")
    logger.info(f"[관련 영상] 검색 키워드: {keywords}")

    if not api_key:
        logger.warning("[관련 영상] YOUTUBE_API_KEY 없음 → 검색 불가")
        return []

    from googleapiclient.discovery import build

    for idx, keyword in enumerate(keywords[:2]):
        search_type = "relevance" if idx == 0 else "popular"
        logger.info(f"[관련 영상] [{idx+1}/{len(keywords[:2])}] 키워드='{keyword}' type={search_type} 검색 시작")

        try:
            youtube = build("youtube", "v3", developerKey=api_key)

            # Step 1: relevance 순으로 최대 15개 검색
            search_res = youtube.search().list(
                q=keyword,
                part="snippet",
                maxResults=15,
                type="video",
                order="relevance",
                relevanceLanguage="ko",
                videoDuration="medium",
            ).execute()

            items = search_res.get("items", [])
            logger.info(f"[관련 영상] '{keyword}' 검색 결과: {len(items)}개 (medium)")

            # medium 결과 없으면 long으로 보완
            if not items:
                search_res = youtube.search().list(
                    q=keyword,
                    part="snippet",
                    maxResults=15,
                    type="video",
                    order="relevance",
                    relevanceLanguage="ko",
                    videoDuration="long",
                ).execute()
                items = search_res.get("items", [])
                logger.info(f"[관련 영상] '{keyword}' long 재검색: {len(items)}개")

            if not items:
                logger.warning(f"[관련 영상] '{keyword}' 검색 결과 없음 → 스킵")
                continue

            # Step 2: 통계 + 영상 길이 일괄 조회
            video_ids = [item["id"]["videoId"] for item in items]
            stats_res = youtube.videos().list(
                part="statistics,contentDetails",
                id=",".join(video_ids),
            ).execute()
            stats_map = {
                item["id"]: {
                    "statistics": item.get("statistics", {}),
                    "duration": item.get("contentDetails", {}).get("duration", ""),
                }
                for item in stats_res.get("items", [])
            }
            logger.info(f"[관련 영상] '{keyword}' 통계 조회: {len(stats_map)}개")

            # Step 3: 후보 구성 (쇼츠 제외)
            candidates = []
            for item in items:
                vid = item["id"]["videoId"]
                if vid in seen_ids:
                    continue
                snippet = item["snippet"]
                item_data = stats_map.get(vid, {})
                stats = item_data.get("statistics", {})

                duration_sec = _parse_duration_seconds(item_data.get("duration", ""))
                if duration_sec < 180:
                    logger.debug(f"[관련 영상] 쇼츠 제외: '{snippet['title'][:30]}' ({duration_sec}s)")
                    continue

                view_count = int(stats.get("viewCount", 0))
                published_at = snippet.get("publishedAt", "")
                velocity = 0.0
                if published_at:
                    try:
                        pub_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                        days = max((datetime.now(timezone.utc) - pub_date).days, 1)
                        velocity = view_count / days
                    except Exception:
                        pass

                candidates.append({
                    "video_id": vid,
                    "title": snippet["title"],
                    "channel": snippet["channelTitle"],
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "thumbnail": f"https://img.youtube.com/vi/{vid}/mqdefault.jpg",
                    "view_count": view_count,
                    "published_at": published_at,
                    "view_velocity": round(velocity, 1),
                    "search_keyword": keyword,
                    "search_type": search_type,
                })

            logger.info(f"[관련 영상] '{keyword}' 유효 후보: {len(candidates)}개 (쇼츠 제외 후)")

            if not candidates:
                logger.warning(f"[관련 영상] '{keyword}' 유효 후보 없음 → 스킵")
                continue

            # Step 4: 선택 기준
            if search_type == "relevance":
                # 관련도순: 첫 번째 후보 (API가 이미 relevance 순)
                best = candidates[0]
            else:
                # 인기순: view_velocity 기준 정렬
                candidates.sort(key=lambda x: x["view_velocity"], reverse=True)
                best = candidates[0]

            seen_ids.add(best["video_id"])
            results.append(best)
            logger.info(
                f"[관련 영상] ✅ 선택됨 [{search_type}] '{best['title'][:40]}' "
                f"(조회수={best['view_count']:,}, velocity={best['view_velocity']:.1f}/day)"
            )

        except Exception as e:
            logger.error(f"[관련 영상] '{keyword}' 검색 오류: {e}", exc_info=True)

    logger.info(f"[관련 영상] 최종 결과: {len(results)}개")
    return results


def _search_youtube_videos(queries: List[str], max_results: int = 5) -> List[Dict]:
    """
    YouTube API를 사용하여 영상 검색
    
    Args:
        queries: 검색 쿼리 리스트
        max_results: 쿼리당 최대 결과 수
    
    Returns:
        영상 정보 리스트
    """
    all_videos = []
    
    # YouTubeService의 search_popular_videos 메서드 활용
    # (실제로는 DB 세션 없이 API만 호출하도록 수정 필요)
    
    for query in queries:
        try:
            # 실전: YouTube Data API v3 호출
            import os
            from googleapiclient.discovery import build

            api_key = os.getenv("YOUTUBE_API_KEY")
            if not api_key:
                logger.warning("YOUTUBE_API_KEY Missing, using Mock")
                videos = _mock_youtube_search(query, max_results)
            else:
                logger.info(f"YouTube API 호출: {query}")
                youtube = build("youtube", "v3", developerKey=api_key)
                
                req = youtube.search().list(
                    q=query,
                    part="snippet",
                    maxResults=max_results,
                    type="video",
                    order="viewCount"
                )
                res = req.execute()
                
                videos = []
                for item in res.get("items", []):
                    vid = item["id"]["videoId"]
                    snippet = item["snippet"]
                    
                    # 통계 정보 추가 조회 (조회수 등)
                    stats_req = youtube.videos().list(
                        part="statistics",
                        id=vid
                    )
                    stats_res = stats_req.execute()
                    stats = stats_res["items"][0]["statistics"] if stats_res["items"] else {}
                    
                    videos.append({
                        "video_id": vid,
                        "title": snippet["title"],
                        "channel_title": snippet["channelTitle"],
                        "view_count": int(stats.get("viewCount", 0)),
                        "like_count": int(stats.get("likeCount", 0)),
                        "comment_count": int(stats.get("commentCount", 0)),
                        "published_at": snippet["publishedAt"],
                        "url": f"https://www.youtube.com/watch?v={vid}"
                    })

            all_videos.extend(videos)
            
        except Exception as e:
            logger.warning(f"쿼리 '{query}' 검색 실패: {e}")
            # 실패 시 Mock으로 폴백 (테스트 안전성)
            videos = _mock_youtube_search(query, max_results)
            all_videos.extend(videos)
            continue
    
    # 중복 제거 (video_id 기준)
    seen_ids = set()
    unique_videos = []
    for v in all_videos:
        vid = v.get("video_id")
        if vid and vid not in seen_ids:
            seen_ids.add(vid)
            unique_videos.append(v)
    
    return unique_videos[:10]  # 최대 10개만 반환


def _mock_youtube_search(query: str, max_results: int) -> List[Dict]:
    """
    Mock YouTube 검색 (실제 API 연동 전 테스트용)
    실제 배포 시에는 youtube_service.py의 로직으로 교체
    """
    # 실제로는 YouTube Data API v3 호출
    # 지금은 구조만 반환
    return [
        {
            "video_id": f"mock_{i}_{query[:10]}",
            "title": f"{query} 관련 영상 {i+1}",
            "channel_title": f"채널 {i+1}",
            "view_count": 10000 * (i+1),
            "like_count": 500 * (i+1),
            "comment_count": 50 * (i+1),
            "published_at": "2024-01-01T00:00:00Z",
            "url": f"https://youtube.com/watch?v=mock_{i}"
        }
        for i in range(min(max_results, 3))
    ]


# =============================================================================
# 헬퍼
# =============================================================================

def _parse_duration_seconds(duration: str) -> int:
    """ISO 8601 duration (PT#H#M#S) → 초 단위 정수로 변환.
    예) 'PT5M30S' → 330,  'PT1H2M3S' → 3723,  'PT45S' → 45
    """
    import re
    if not duration:
        return 0
    m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not m:
        return 0
    h = int(m.group(1) or 0)
    mi = int(m.group(2) or 0)
    s = int(m.group(3) or 0)
    return h * 3600 + mi * 60 + s


# =============================================================================
# 키워드별 인기 영상 1개 선택 (research_only 모드용)
# =============================================================================

def search_top_video_per_keyword(keywords: List[str]) -> List[Dict]:
    """
    각 키워드당 기간 대비 조회수 증가율(view velocity)이 가장 높은 영상 1개씩 반환.

    velocity = view_count / days_since_publish
    """
    import os
    from datetime import datetime, timezone

    api_key = os.getenv("YOUTUBE_API_KEY")
    results: List[Dict] = []
    seen_ids: set = set()

    for keyword in keywords:
        try:
            if not api_key:
                logger.warning(f"YOUTUBE_API_KEY 없음 - '{keyword}' 스킵")
                continue

            from googleapiclient.discovery import build
            youtube = build("youtube", "v3", developerKey=api_key)

            # relevance 순으로 15개 검색 (쇼츠 제외 후 후보 확보)
            search_res = youtube.search().list(
                q=keyword,
                part="snippet",
                maxResults=15,
                type="video",
                order="relevance",
                relevanceLanguage="ko",
                videoDuration="medium",   # 4~20분 (미드폼 우선)
            ).execute()

            # medium 결과 없으면 long 으로 보완
            if not search_res.get("items"):
                search_res = youtube.search().list(
                    q=keyword,
                    part="snippet",
                    maxResults=15,
                    type="video",
                    order="relevance",
                    relevanceLanguage="ko",
                    videoDuration="long",
                ).execute()

            video_ids = [
                item["id"]["videoId"]
                for item in search_res.get("items", [])
            ]
            if not video_ids:
                logger.warning(f"유튜브 '{keyword}': 검색 결과 없음")
                continue

            # 통계 + 영상 길이 일괄 조회
            stats_res = youtube.videos().list(
                part="statistics,contentDetails",
                id=",".join(video_ids),
            ).execute()
            stats_map = {
                item["id"]: {
                    "statistics": item.get("statistics", {}),
                    "duration": item.get("contentDetails", {}).get("duration", ""),
                }
                for item in stats_res.get("items", [])
            }

            candidates = []
            for item in search_res.get("items", []):
                vid = item["id"]["videoId"]
                if vid in seen_ids:
                    continue
                snippet = item["snippet"]
                item_data = stats_map.get(vid, {})
                stats = item_data.get("statistics", {})

                # 쇼츠·짧은 영상 제외: 3분(180초) 미만 스킵
                duration_sec = _parse_duration_seconds(item_data.get("duration", ""))
                if duration_sec < 180:
                    logger.debug(f"쇼츠/짧은 영상 제외: {snippet['title'][:30]} ({duration_sec}s)")
                    continue

                view_count = int(stats.get("viewCount", 0))
                published_at = snippet.get("publishedAt", "")

                # 기간당 조회수 증가율 계산
                velocity = 0.0
                if published_at:
                    pub_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                    days = max((datetime.now(timezone.utc) - pub_date).days, 1)
                    velocity = view_count / days

                candidates.append({
                    "video_id": vid,
                    "title": snippet["title"],
                    "channel": snippet["channelTitle"],
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "thumbnail": f"https://img.youtube.com/vi/{vid}/mqdefault.jpg",
                    "view_count": view_count,
                    "published_at": published_at,
                    "view_velocity": round(velocity, 1),
                    "search_keyword": keyword,
                })

            if not candidates:
                continue

            # 기간당 조회수 증가율 기준 정렬 후 1위 선택
            candidates.sort(key=lambda x: x["view_velocity"], reverse=True)
            best = candidates[0]
            seen_ids.add(best["video_id"])
            results.append(best)
            logger.info(
                f"유튜브 '{keyword}': '{best['title'][:40]}' "
                f"(velocity: {best['view_velocity']:.0f} views/day)"
            )

        except Exception as e:
            logger.warning(f"유튜브 검색 오류 ({keyword}): {e}")

    return results


# =============================================================================
# 실제 YouTube API 연동 (Phase 2)
# =============================================================================

# async def _real_youtube_search(query: str, max_results: int) -> List[Dict]:
#     """
#     실제 YouTube Data API v3 연동
#     app/services/youtube_service.py의 로직 활용
#     """
#     from app.core.config import settings
#     import httpx
#     
#     BASE_URL = "https://www.googleapis.com/youtube/v3"
#     params = {
#         "part": "snippet,statistics",
#         "q": query,
#         "type": "video",
#         "maxResults": max_results,
#         "order": "viewCount",
#         "key": settings.youtube_api_key
#     }
#     
#     async with httpx.AsyncClient() as client:
#         resp = await client.get(f"{BASE_URL}/search", params=params)
#         resp.raise_for_status()
#         data = resp.json()
#         
#         # 파싱 로직...
#         return parsed_videos
