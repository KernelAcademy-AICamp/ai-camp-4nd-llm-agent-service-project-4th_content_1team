"""
페르소나 API 스키마
"""
from typing import List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class PersonaResponse(BaseModel):
    """페르소나 조회 응답."""

    id: str
    channel_id: str

    # 종합 서술
    persona_summary: Optional[str] = None

    # 정체성
    one_liner: Optional[str] = None
    main_topics: Optional[List[str]] = None
    content_style: Optional[str] = None
    differentiator: Optional[str] = None

    # 타겟 시청자
    target_audience: Optional[str] = None
    audience_needs: Optional[str] = None

    # 성공 공식
    hit_topics: Optional[List[str]] = None
    title_patterns: Optional[List[str]] = None
    optimal_duration: Optional[str] = None

    # 성장 기회
    growth_opportunities: Optional[List[str]] = None

    # 근거
    evidence: Optional[List[Any]] = None

    # 카테고리 (주제 추천 필터용)
    analyzed_categories: Optional[List[str]] = None      # 채널 분석에서 추출
    analyzed_subcategories: Optional[List[str]] = None   # 채널 분석에서 추출
    preferred_categories: Optional[List[str]] = None     # 사용자 선택
    preferred_subcategories: Optional[List[str]] = None  # 사용자 선택

    # 매칭용 키워드
    topic_keywords: Optional[List[str]] = None
    style_keywords: Optional[List[str]] = None

    # 메타
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PersonaUpdateRequest(BaseModel):
    """페르소나 수정 요청."""

    persona_summary: Optional[str] = Field(None, description="종합 요약")
    one_liner: Optional[str] = Field(None, description="한 줄 정의")
    main_topics: Optional[List[str]] = Field(None, description="주요 주제")
    content_style: Optional[str] = Field(None, description="콘텐츠 스타일")
    differentiator: Optional[str] = Field(None, description="차별화 포인트")
    target_audience: Optional[str] = Field(None, description="타겟 시청자")
    audience_needs: Optional[str] = Field(None, description="시청자 니즈")
    hit_topics: Optional[List[str]] = Field(None, description="히트 주제")
    title_patterns: Optional[List[str]] = Field(None, description="제목 패턴")
    optimal_duration: Optional[str] = Field(None, description="적정 영상 길이")
    growth_opportunities: Optional[List[str]] = Field(None, description="성장 기회")
    topic_keywords: Optional[List[str]] = Field(None, description="주제 키워드")
    style_keywords: Optional[List[str]] = Field(None, description="스타일 키워드")
    preferred_categories: Optional[List[str]] = Field(None, description="선호 카테고리 (사용자 선택)")
    preferred_subcategories: Optional[List[str]] = Field(None, description="선호 서브카테고리 (사용자 선택)")


class PersonaGenerateResponse(BaseModel):
    """페르소나 생성 응답."""

    success: bool
    message: str
    persona: Optional[PersonaResponse] = None
