from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class CommentInsights(BaseModel):
    """시청자 반응 분석"""
    reactions: List[str] = Field(default_factory=list, description="시청자들의 주요 반응")
    needs: List[str] = Field(default_factory=list, description="시청자들이 원하는 콘텐츠/니즈")

class VideoAnalysis(BaseModel):
    """개별 경쟁 영상 분석 결과 (분석 페이지와 동일한 구조)"""
    video_id: str = Field(description="유튜브 비디오 ID")
    title: str = Field(description="영상 제목")
    
    strengths: List[str] = Field(default_factory=list, description="이 영상이 잘 된 이유 (성공이유)")
    weaknesses: List[str] = Field(default_factory=list, description="이 영상에서 아쉬운 점 (부족한점)")
    applicable_points: List[str] = Field(default_factory=list, description="내 채널에 적용할 수 있는 구체적 액션 아이템")
    comment_insights: CommentInsights = Field(default_factory=CommentInsights, description="시청자 반응 분석")

class CrossInsights(BaseModel):
    """여러 영상에 걸친 공통 인사이트"""
    common_patterns: List[str] = Field(default_factory=list, description="상위 영상들의 공통 성공 공식")
    common_gaps: List[str] = Field(default_factory=list, description="상위 영상들이 모두 놓치고 있는 빈틈 (기회)")
    differentiation_ideas: List[str] = Field(default_factory=list, description="우리 영상이 시도해볼 만한 차별화 아이디어")
    do_and_dont: List[str] = Field(default_factory=list, description="반드시 해야 할 것(Do)과 하지 말아야 할 것(Don't)")

class CompetitorAnalysisResult(BaseModel):
    """Competitor Analyzer 노드의 최종 출력"""
    collection_id: Optional[str] = Field(None, description="DB에 저장된 컬렉션 ID (있을 경우)")
    video_analyses: List[VideoAnalysis] = Field(default_factory=list, description="개별 영상 분석 리스트")
    cross_insights: Optional[CrossInsights] = Field(None, description="종합 인사이트")
    analyzed_at: str = Field(default="", description="분석 시점 (ISO format)")
