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
    """
    logger.info("YouTube Fetcher Node 시작")
    
    # 1. 입력 데이터 추출
    topic = state.get("topic", "")
    content_brief = state.get("content_brief", {})
    search_queries = content_brief.get("search_queries", [])
    
    # 검색 쿼리가 없으면 주제를 그대로 사용
    if not search_queries:
        search_queries = [topic]
    
    logger.info(f"검색 쿼리: {search_queries[:3]}")  # 상위 3개만 로깅
    
    # 2. YouTube 검색 (동기 방식)
    # 실제 DB 연결 없이 API만 호출 (State 기반 워크플로우)
    try:
        videos = _search_youtube_videos(search_queries[:2])  # 상위 2개 쿼리만 사용
        
        logger.info(f"검색 완료: {len(videos)}개 영상 발견")
        
        # 3. State 업데이트
        return {
            "youtube_data": {
                "videos": videos,
                "search_queries_used": search_queries[:2]
            }
        }
        
    except Exception as e:
        logger.error(f"YouTube 검색 실패: {e}", exc_info=True)
        # 실패해도 파이프라인은 계속 진행 (빈 데이터 반환)
        return {
            "youtube_data": {
                "videos": [],
                "error": str(e)
            }
        }


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
