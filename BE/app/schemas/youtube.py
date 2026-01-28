from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime


# Request
class VideoSearchRequest(BaseModel):
    """YouTube 비디오 검색 요청 스키마"""
    
    keywords: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="검색 키워드 (필수)"
    )
    title: Optional[str] = Field(
        None,
        max_length=100,
        description="제목 필터 (선택)"
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=50,
        description="반환할 최대 결과 수 (기본 10, 최대 50)"
    )

    @validator('keywords')
    def validate_keywords(cls, v):
        """키워드 유효성 검사"""
        if not v.strip():
            raise ValueError("키워드는 공백일 수 없습니다")
        return v.strip()


# Response
class VideoStatistics(BaseModel):
    """비디오 통계 정보"""
    
    view_count: int = Field(default=0, description="조회수")
    like_count: int = Field(default=0, description="좋아요 수")
    comment_count: int = Field(default=0, description="댓글 수")


class VideoItem(BaseModel):
    """비디오 상세 정보"""
    
    video_id: str = Field(..., description="YouTube 비디오 ID")
    title: str = Field(..., description="비디오 제목")
    description: str = Field(default="", description="비디오 설명")
    thumbnail_url: str = Field(..., description="썸네일 URL")
    channel_id: str = Field(..., description="채널 ID")
    channel_title: str = Field(..., description="채널 이름")
    published_at: datetime = Field(..., description="업로드 날짜")
    statistics: VideoStatistics = Field(..., description="통계 정보")
    popularity_score: float = Field(
        ...,
        description="트렌드 인기도 점수 (일일 조회수 × 신선도 + 참여도)"
    )
    days_since_upload: int = Field(
        ...,
        description="업로드 후 경과 일수"
    )


class VideoSearchResponse(BaseModel):
    """YouTube 비디오 검색 응답 스키마"""
    
    total_results: int = Field(..., description="검색 결과 총 개수")
    query: str = Field(..., description="실제 사용된 검색 쿼리")
    videos: List[VideoItem] = Field(default=[], description="비디오 목록")
