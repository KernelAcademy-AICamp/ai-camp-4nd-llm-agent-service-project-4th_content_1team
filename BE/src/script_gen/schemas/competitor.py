from typing import List, Optional
from pydantic import BaseModel, Field

class VideoAnalysis(BaseModel):
    """개별 경쟁 영상 분석 결과"""
    video_id: str = Field(description="유튜브 비디오 ID")
    title: str = Field(description="영상 제목")
    hook_analysis: str = Field(description="초반 30초 훅 전략 분석 (무엇이 시청자를 잡았나)")
    content_structure: List[str] = Field(description="영상 구성/목차 요약")
    
    strong_points: List[str] = Field(description="이 영상의 강점 (배울 점)")
    weak_points: List[str] = Field(description="이 영상의 약점 (우리가 공략할 점)")
    
    comment_themes: List[str] = Field(description="댓글에서 보이는 시청자들의 주요 반응/불만")

class CrossInsights(BaseModel):
    """여러 영상에 걸친 공통 인사이트"""
    common_patterns: List[str] = Field(description="상위 영상들의 공통 성공 공식")
    common_gaps: List[str] = Field(description="상위 영상들이 모두 놓치고 있는 빈틈 (기회)")
    differentiation_ideas: List[str] = Field(description="우리 영상이 시도해볼 만한 차별화 아이디어")
    do_and_dont: List[str] = Field(description="반드시 해야 할 것(Do)과 하지 말아야 할 것(Don't)")

class CompetitorAnalysisResult(BaseModel):
    """Competitor Analyzer 노드의 최종 출력"""
    collection_id: Optional[str] = Field(None, description="DB에 저장된 컬렉션 ID (있을 경우)")
    video_analyses: List[VideoAnalysis] = Field(description="개별 영상 분석 리스트")
    cross_insights: CrossInsights = Field(description="종합 인사이트")
    analyzed_at: str = Field(description="분석 시점 (ISO format)")
