from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# =============================================================================
# Output Structures (Writer가 생성하는 최종 결과물)
# =============================================================================

class OnScreenCue(BaseModel):
    """화면에 표시할 시각 요소"""
    type: Literal["text", "image", "table", "chart", "broll", "screenshot"]
    ref: Optional[str] = Field(None, description="참조할 리소스 ID (fact_id, article_id 등)")
    caption: str = Field(description="화면에 표시할 텍스트/설명")
    timing_sec: Optional[List[int]] = Field(None, description="[시작초, 종료초] - Phase 2에서 추가")

class Beat(BaseModel):
    """챕터 내의 개별 문단/비트"""
    beat_id: str
    purpose: Literal["setup", "evidence", "contrast", "insight", "example", "cta"]
    line: str = Field(description="실제 나레이션 텍스트")
    fact_references: List[str] = Field(default=[], description="이 비트에서 인용한 Fact ID 리스트 (예: ['fact-abc123', 'fact-def456'])")
    claims: List[str] = Field(default=[], description="이 비트에서 사용된 Claim ID 리스트")
    on_screen_cues: List[OnScreenCue] = Field(default=[])
    broll_ideas: List[str] = Field(default=[], description="B-roll 촬영/편집 아이디어")

class Chapter(BaseModel):
    """대본의 챕터 (Insight Blueprint의 chapter 구조를 따름)"""
    chapter_id: str
    title: str
    narration: str = Field(description="챕터 전체 나레이션 (beats의 line을 합친 것)")
    beats: List[Beat] = Field(description="챕터를 구성하는 비트들")

class Hook(BaseModel):
    """영상 시작 15초 훅"""
    text: str = Field(description="훅 나레이션")
    fact_references: List[str] = Field(default=[], description="훅에서 인용한 Fact ID 리스트")
    on_screen_cues: List[OnScreenCue] = Field(default=[])
    claims: List[str] = Field(default=[], description="훅에서 사용된 Claim ID")

class Closing(BaseModel):
    """영상 마무리"""
    text: str = Field(description="마무리 멘트")
    cta: str = Field(description="Call-to-Action (구독/좋아요 유도)")

class Script(BaseModel):
    """전체 대본 구조"""
    hook: Hook
    chapters: List[Chapter]
    closing: Closing

class Claim(BaseModel):
    """대본에서 사용된 주장/사실 (Source Binding용)"""
    claim_id: str
    text: str = Field(description="주장 원문")
    type: Literal["stat", "event", "definition", "trend", "quote", "opinion"]
    linked_fact_ids: List[str] = Field(default=[], description="이 주장을 뒷받침하는 Fact ID")
    risk_flags: List[str] = Field(default=[], description="unsourced, warning_used_in_hook 등")

class SourceMapEntry(BaseModel):
    """Claim과 Fact의 연결 정보 (출처 추적용)"""
    claim_id: str
    fact_id: str
    evidence: dict = Field(description="article_id, url, publisher, snippet 등")

class QualityReport(BaseModel):
    """대본 품질 리포트"""
    used_fact_ids: List[str] = Field(description="실제 사용된 Fact ID")
    unused_required_fact_ids: List[str] = Field(default=[], description="필수였지만 안 쓴 Fact")
    warnings_used: List[dict] = Field(default=[], description="경고 있는 Fact 사용 내역")
    policy_checks: dict = Field(description="noUnsourcedNumbers, hookWarningsBlocked 등")

class ScriptDraft(BaseModel):
    """Writer 에이전트의 최종 출력"""
    script_draft_id: str
    topic_request_id: Optional[str] = None
    generated_at: str
    
    metadata: dict = Field(description="title, hookType, estimatedDurationMin, readingLevel")
    script: Script
    claims: List[Claim]
    source_map: List[SourceMapEntry]
    quality_report: QualityReport


# =============================================================================
# Input Structures (Writer가 받는 입력 - 간소화 버전)
# =============================================================================

class WriterInput(BaseModel):
    """Writer Node가 State에서 받을 입력 데이터 구조"""
    topic_request_id: Optional[str] = None
    channel_profile: dict
    insight_blueprint: dict  # InsightPack (from Insight Builder)
    fact_pack: dict  # structured_facts + visual_plan
    competitor_pack: Optional[dict] = None  # CompetitorAnalysisResult
    output_spec: dict = Field(default={"language": "ko", "scriptLength": "standard"})
