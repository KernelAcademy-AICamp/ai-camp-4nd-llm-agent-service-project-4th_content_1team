from pydantic import BaseModel, Field
from typing import List, Optional


class ChannelSearchRequest(BaseModel):
    """채널 검색 요청"""
    query: str = Field(..., min_length=1, description="채널 이름, URL, 또는 @핸들")


class ChannelSearchResult(BaseModel):
    """채널 검색 결과"""
    channel_id: str
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    subscriber_count: int
    view_count: int
    video_count: int
    custom_url: Optional[str] = None


class ChannelSearchResponse(BaseModel):
    """채널 검색 응답"""
    total_results: int
    channels: List[ChannelSearchResult]


class ChannelStatusResponse(BaseModel):
    """채널 상태 확인 응답 (온보딩 분기용)"""
    has_channel: bool
    channel_id: Optional[str] = None
    video_count: int = 0
    total_duration_minutes: float = 0.0
    has_enough_videos: bool = False
