import logging
import re
from typing import List, Dict, Any, Optional
import httpx
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


class ChannelService:
    """YouTube 채널 검색 및 정보 조회 서비스"""

    BASE_URL = "https://www.googleapis.com/youtube/v3"

    @staticmethod
    def extract_channel_id_from_url(query: str) -> Optional[str]:
        """
        URL에서 채널 ID 추출
        
        지원 형식:
        - https://www.youtube.com/channel/UCxxxx
        - https://www.youtube.com/@username
        - https://youtube.com/c/channelname
        """
        # 채널 ID 직접 추출 (UC로 시작하는 24자)
        channel_id_match = re.search(r'UC[\w-]{22}', query)
        if channel_id_match:
            return channel_id_match.group(0)
        
        # @핸들 추출
        handle_match = re.search(r'@([\w-]+)', query)
        if handle_match:
            return f"@{handle_match.group(1)}"
        
        # /c/ 또는 /user/ 형식
        custom_match = re.search(r'youtube\.com/(?:c|user)/([\w-]+)', query)
        if custom_match:
            return custom_match.group(1)
        
        return None

    @staticmethod
    async def search_channels(
        query: str,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        채널 검색
        
        Args:
            query: 채널 이름, URL, 또는 @핸들
            max_results: 최대 결과 수
            
        Returns:
            채널 정보 리스트
        """
        api_key = settings.youtube_api_key
        
        # URL에서 채널 ID 추출 시도
        extracted_id = ChannelService.extract_channel_id_from_url(query)
        
        if extracted_id:
            # 직접 채널 정보 조회
            return await ChannelService._get_channel_by_id(extracted_id, api_key)
        
        # 검색어로 채널 검색
        return await ChannelService._search_channels_by_keyword(
            query, api_key, max_results
        )

    @staticmethod
    async def _get_channel_by_id(
        channel_id: str,
        api_key: str
    ) -> List[Dict[str, Any]]:
        """채널 ID로 직접 조회"""
        params = {
            "part": "snippet,statistics",
            "key": api_key
        }
        
        # @핸들이면 forHandle, 아니면 id
        if channel_id.startswith("@"):
            params["forHandle"] = channel_id[1:]
        else:
            params["id"] = channel_id
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{ChannelService.BASE_URL}/channels",
                    params=params
                )
                
                if resp.status_code == 403:
                    raise HTTPException(status_code=429, detail="YouTube API 할당량 초과")
                
                resp.raise_for_status()
                data = resp.json()
                
                items = data.get("items", [])
                if not items:
                    return []
                
                channels = [ChannelService._parse_channel_item(item) for item in items]
                
                # 구독자 많은 순 정렬
                channels.sort(key=lambda x: x.get("subscriber_count", 0), reverse=True)
                
                return channels
        
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="YouTube API 타임아웃")
        except httpx.HTTPStatusError as e:
            logger.error(f"YouTube API error: {e}")
            raise HTTPException(status_code=500, detail=f"채널 조회 실패: {str(e)}")

    @staticmethod
    async def _search_channels_by_keyword(
        keyword: str,
        api_key: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """키워드로 채널 검색"""
        # 1. search.list로 채널 ID 수집
        search_params = {
            "part": "id",
            "q": keyword,
            "type": "channel",
            "maxResults": max_results,
            "order": "relevance",
            "key": api_key
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                search_resp = await client.get(
                    f"{ChannelService.BASE_URL}/search",
                    params=search_params
                )
                
                if search_resp.status_code == 403:
                    raise HTTPException(status_code=429, detail="YouTube API 할당량 초과")
                
                search_resp.raise_for_status()
                search_data = search_resp.json()
                
                channel_ids = [
                    item["id"]["channelId"]
                    for item in search_data.get("items", [])
                    if item.get("id", {}).get("channelId")
                ]
                
                if not channel_ids:
                    return []
                
                # 2. channels.list로 상세 정보 조회
                channels_params = {
                    "part": "snippet,statistics",
                    "id": ",".join(channel_ids),
                    "key": api_key
                }
                
                channels_resp = await client.get(
                    f"{ChannelService.BASE_URL}/channels",
                    params=channels_params
                )
                channels_resp.raise_for_status()
                channels_data = channels_resp.json()
                
                # 파싱
                channels = [
                    ChannelService._parse_channel_item(item)
                    for item in channels_data.get("items", [])
                ]
                
                # 관련성 점수 추가
                for ch in channels:
                    ch["relevance_score"] = ChannelService._calculate_relevance(
                        ch["title"], keyword
                    )
                
                # 정렬: 관련성 우선 → 구독자 수
                channels.sort(
                    key=lambda x: (
                        -x.get("relevance_score", 0),  # 관련성 높은 순
                        -x.get("subscriber_count", 0)  # 구독자 많은 순
                    )
                )
                
                return channels
        
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="YouTube API 타임아웃")
        except httpx.HTTPStatusError as e:
            logger.error(f"YouTube API error: {e}")
            raise HTTPException(status_code=500, detail=f"채널 검색 실패: {str(e)}")

    @staticmethod
    def _calculate_relevance(title: str, query: str) -> int:
        """
        채널 제목과 검색어의 관련성 점수 계산
        
        Returns:
            0~100 점수 (높을수록 정확히 일치)
        """
        title_lower = title.lower().strip()
        query_lower = query.lower().strip()
        
        # 완전 일치
        if title_lower == query_lower:
            return 100
        
        # 검색어가 제목에 정확히 포함
        if query_lower in title_lower:
            # 제목 시작에 있으면 더 높은 점수
            if title_lower.startswith(query_lower):
                return 90
            return 80
        
        # 검색어의 모든 단어가 제목에 포함
        query_words = query_lower.split()
        title_words_set = set(title_lower.split())
        matches = sum(1 for word in query_words if word in title_words_set)
        
        if matches == len(query_words):
            return 70
        elif matches > 0:
            return 50 + (matches / len(query_words)) * 20
        
        return 0

    @staticmethod
    def _parse_channel_item(item: Dict[str, Any]) -> Dict[str, Any]:
        """API 응답을 표준 형식으로 변환"""
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})
        
        return {
            "channel_id": item.get("id"),
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url") or
                           snippet.get("thumbnails", {}).get("default", {}).get("url"),
            "subscriber_count": int(statistics.get("subscriberCount", 0)),
            "view_count": int(statistics.get("viewCount", 0)),
            "video_count": int(statistics.get("videoCount", 0)),
            "custom_url": snippet.get("customUrl"),
        }

    @staticmethod
    async def get_channel_recent_videos(
        channel_id: str,
        max_results: int = 3,
        api_key: str = None
    ) -> List[Dict[str, Any]]:
        """
        채널의 최신 영상 조회
        
        Args:
            channel_id: YouTube 채널 ID
            max_results: 가져올 영상 수 (기본 3개)
            api_key: YouTube Data API 키
            
        Returns:
            최신 영상 리스트
        """
        if not api_key:
            api_key = settings.youtube_api_key
        
        # search.list로 채널의 최신 영상 검색
        search_params = {
            "part": "id",
            "channelId": channel_id,
            "type": "video",
            "order": "date",  # 최신순
            "maxResults": max_results,
            "key": api_key
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # 1. 영상 ID 수집
                search_resp = await client.get(
                    f"{ChannelService.BASE_URL}/search",
                    params=search_params
                )
                
                if search_resp.status_code == 403:
                    raise HTTPException(status_code=429, detail="YouTube API 할당량 초과")
                
                search_resp.raise_for_status()
                search_data = search_resp.json()
                
                # 중복 제거하면서 순서 유지
                seen = set()
                video_ids = []
                for item in search_data.get("items", []):
                    vid = item.get("id", {}).get("videoId")
                    if vid and vid not in seen:
                        seen.add(vid)
                        video_ids.append(vid)

                if not video_ids:
                    return []
                
                # 2. 영상 상세 정보 조회
                videos_params = {
                    "part": "snippet,statistics,contentDetails",
                    "id": ",".join(video_ids),
                    "key": api_key
                }
                
                videos_resp = await client.get(
                    f"{ChannelService.BASE_URL}/videos",
                    params=videos_params
                )
                videos_resp.raise_for_status()
                videos_data = videos_resp.json()
                
                # 3. 파싱
                videos = []
                for item in videos_data.get("items", []):
                    snippet = item.get("snippet", {})
                    stats = item.get("statistics", {})
                    content_details = item.get("contentDetails", {})
                    
                    videos.append({
                        "video_id": item.get("id"),
                        "title": snippet.get("title", ""),
                        "description": snippet.get("description", ""),
                        "thumbnail_url": snippet.get("thumbnails", {}).get("medium", {}).get("url"),
                        "published_at": snippet.get("publishedAt"),
                        "view_count": int(stats.get("viewCount", 0)),
                        "like_count": int(stats.get("likeCount", 0)),
                        "comment_count": int(stats.get("commentCount", 0)),
                        "duration": content_details.get("duration"),
                    })
                
                return videos
        
        except httpx.TimeoutException:
            logger.error(f"YouTube API timeout for channel: {channel_id}")
            raise HTTPException(status_code=504, detail="YouTube API 타임아웃")
        except httpx.HTTPStatusError as e:
            logger.error(f"YouTube API error: {e}")
            raise HTTPException(status_code=500, detail=f"영상 조회 실패: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return []
