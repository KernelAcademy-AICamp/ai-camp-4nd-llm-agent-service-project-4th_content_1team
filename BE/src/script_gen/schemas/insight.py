from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class CompetitorEvidence(BaseModel):
    """경쟁 영상의 갭이나 약점"""
    video_ref_id: str = Field(description="경쟁 영상 참조 ID")
    gap_snippet: str = Field(description="발견된 갭이나 약점 설명")

class InsightSupporting(BaseModel):
    """차별화 포인트에 대한 근거"""
    fact_ids: List[str] = Field(description="뒷받침할 팩트 ID 리스트")
    competitor_evidence: List[CompetitorEvidence] = Field(default=[], description="경쟁 영상의 갭이나 약점")

class InsightDifferentiator(BaseModel):
    """경쟁 영상과의 차별화 포인트"""
    type: Literal["myth_busting", "counterargument", "framework", "checklist", "case_study", "prediction_with_bounds"] = Field(description="차별화 유형")
    title: str = Field(description="차별화 포인트 제목")
    description: str = Field(description="상세 설명")
    why_unique_vs_competitors: str = Field(description="경쟁 영상들과 구체적으로 무엇이 다른지")
    supporting: InsightSupporting = Field(description="근거 자료")

class InsightHookScript(BaseModel):
    """훅 대본 후보"""
    id: str = Field(description="스크립트 ID (h1, h2...)")
    text: str = Field(description="실제 훅 멘트 (충격적/호기심 자극)")
    uses_fact_ids: List[str] = Field(default=[], description="훅에 사용된 팩트 ID")

class ThumbnailAngle(BaseModel):
    """썸네일 컨셉"""
    concept: str = Field(description="썸네일 컨셉")
    copy_candidates: List[str] = Field(default=[], description="썸네일 문구 후보")
    avoid: List[str] = Field(default=[], description="피해야 할 요소")

class InsightHookPlan(BaseModel):
    """초반 15초(Hook) 전략"""
    hook_type: Literal["shock", "curiosity", "benefit", "controversy", "myth_busting"] = Field(description="훅 전략 유형")
    hook_scripts: List[InsightHookScript] = Field(description="스크립트 후보 2~3개")
    thumbnail_angle: ThumbnailAngle = Field(description="썸네일 컨셉")

class InsightChapterVisual(BaseModel):
    """챕터 내 시각자료 제안"""
    type: Literal["table", "chart", "timeline", "article_image", "text_overlay"]
    ref: Optional[str] = Field(None, description="참조할 데이터나 이미지 소스")
    caption: str = Field(description="화면에 띄울 텍스트나 설명")

class InsightChapter(BaseModel):
    """영상 챕터 설계"""
    chapter_id: str
    title: str
    goal: str = Field(description="이 챕터의 시청자 경험 목표")
    key_points: List[str] = Field(description="다룰 핵심 내용")
    required_facts: List[str] = Field(description="반드시 포함해야 할 팩트 ID")
    visuals: List[InsightChapterVisual] = Field(default=[])
    anti_patterns: List[str] = Field(default=[], description="피해야 할 진부한 설명 방식")

class CallToAction(BaseModel):
    """CTA 설정"""
    primary: str = Field(description="주요 CTA (구독, 좋아요 등)")
    optional: str = Field(default="", description="선택적 CTA")

class StoryStructure(BaseModel):
    """영상 구조"""
    chapters: List[InsightChapter] = Field(description="챕터 리스트")
    call_to_action: CallToAction = Field(description="CTA")

class ClaimPolicy(BaseModel):
    """근거 인용 원칙"""
    no_unsourced_numbers: bool = Field(default=True, description="출처 없는 숫자 금지")
    handle_warnings: Literal["exclude_from_hook", "allow_in_body_with_context", "exclude_all"] = Field(
        default="exclude_from_hook",
        description="경고 있는 팩트 처리 방침"
    )

class InsightPositioning(BaseModel):
    """영상의 핵심 포지셔닝"""
    thesis: str = Field(description="이 주제에 대한 핵심 주장 (Thesis)")
    one_sentence_promise: str = Field(description="시청자에게 약속하는 단 하나의 가치")
    who_is_this_for: str = Field(description="핵심 타겟 시청자")
    what_they_will_get: str = Field(description="시청 후 얻게 될 구체적 이득")

class InsightWriterInstructions(BaseModel):
    """Writer를 위한 지침"""
    tone: str
    reading_level: Literal["beginner", "intermediate", "advanced"]
    must_include: List[str] = Field(default=[])
    must_avoid: List[str] = Field(default=[])
    claim_policy: ClaimPolicy = Field(description="숫자/근거 인용 원칙")

class InsightPack(BaseModel):
    """Insight Builder 최종 결과물"""
    insight_pack_id: str
    positioning: InsightPositioning
    differentiators: List[InsightDifferentiator]
    hook_plan: InsightHookPlan
    story_structure: StoryStructure = Field(description="chapters 리스트와 callToAction 포함")
    writer_instructions: InsightWriterInstructions
