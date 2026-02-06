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
