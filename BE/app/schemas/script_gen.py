"""
Script Generation API Schemas
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# =============================================================================
# Request Schemas
# =============================================================================

class ScriptGenStartRequest(BaseModel):
    """스크립트 생성 시작 요청"""
    
    topic: str = Field(
        ...,
        description="영상 주제",
        example="AI 코딩 도구의 미래"
    )
    
    topic_recommendation_id: Optional[str] = Field(
        None,
        description="AI 추천 주제 ID (선택). recommendations 배열의 인덱스 또는 title",
        example="0"
    )


# =============================================================================
# Response Schemas
# =============================================================================

class ChannelProfileResponse(BaseModel):
    """채널 프로필 응답"""
    
    name: str
    category: str
    target_audience: str
    content_style: Optional[str] = None
    main_topics: Optional[List[str]] = None
    average_duration: Optional[str] = None


class TopicContextResponse(BaseModel):
    """주제 컨텍스트 응답"""
    
    source: str
    trend_basis: str
    urgency: str
    content_angles: List[str]
    recommendation_reason: str
    search_keywords: List[str] = Field(default_factory=list)  # channel_topics/trend_topics 테이블에서 가져온 뉴스 검색 키워드


class PlannerInputResponse(BaseModel):
    """Planner 입력 응답 (디버깅용)"""
    
    topic: str
    channel_profile: ChannelProfileResponse
    topic_context: Optional[TopicContextResponse] = None


class ScriptGenStartResponse(BaseModel):
    """스크립트 생성 시작 응답"""
    
    success: bool
    message: str
    task_id: Optional[str] = Field(
        None,
        description="비동기 작업 ID (향후 구현)"
    )
    planner_input: Optional[PlannerInputResponse] = Field(
        None,
        description="Planner 입력 데이터 (디버깅용)"
    )


# =============================================================================
# Content Brief Response (Planner 출력)
# =============================================================================

class ContentAngle(BaseModel):
    """콘텐츠 앵글"""
    angle: str
    description: str
    hook: str


class ResearchSource(BaseModel):
    """리서치 소스 항목"""
    keyword: str
    how_to_use: str


class ResearchPlan(BaseModel):
    """리서치 플랜"""
    sources: List[ResearchSource]
    youtube_keywords: List[str]


class ContentBriefResponse(BaseModel):
    """콘텐츠 기획안 (Planner 출력)"""
    content_angle: ContentAngle   # 단일 앵글 (Intent Analyzer 앵글을 디벨롭)
    research_plan: ResearchPlan


class ScriptGenPlannerResponse(BaseModel):
    """Planner 완료 응답"""
    
    success: bool
    message: str
    content_brief: Optional[ContentBriefResponse] = None
    error: Optional[str] = None


# =============================================================================
# Full Pipeline Response (최종 결과)
# =============================================================================

class ReferenceResponse(BaseModel):
    """참고 자료 (기사/영상)"""
    title: str
    summary: str
    source: str
    date: Optional[str] = None
    url: str
    analysis: Optional[Dict[str, Any]] = None  # facts, opinions
    images: Optional[List[Dict[str, Any]]] = None  # Base64 이미지


class CompetitorVideoResponse(BaseModel):
    """경쟁 영상 분석 결과"""
    video_id: str
    title: str
    channel: Optional[str] = None
    url: Optional[str] = None
    thumbnail: Optional[str] = None
    hook_analysis: Optional[str] = None
    weak_points: Optional[List[str]] = None
    strong_points: Optional[List[str]] = None


class ScriptChapterResponse(BaseModel):
    """스크립트 챕터"""
    title: str
    content: str  # 전체 내레이션


class ScriptResponse(BaseModel):
    """최종 스크립트"""
    hook: str
    chapters: List[ScriptChapterResponse]
    outro: str


class ScriptGenExecuteResponse(BaseModel):
    """통합 실행 테스트 결과 응답"""
    success: bool
    message: str
    script: Optional[ScriptResponse] = None
    references: Optional[List[ReferenceResponse]] = None
    competitor_videos: Optional[List[CompetitorVideoResponse]] = None  # 경쟁 영상 분석
    citations: Optional[List[Dict[str, Any]]] = None  # ①②③ 인라인 출처 매핑
    topic_request_id: Optional[str] = None  # 새로고침 시 복원용
    error: Optional[str] = None


class ScriptGenTaskResponse(BaseModel):
    """비동기 작업 상태 조회 응답"""
    task_id: str
    status: str = Field(..., description="PENDING, STARTED, SUCCESS, FAILURE")
    result: Optional[ScriptGenExecuteResponse] = None

