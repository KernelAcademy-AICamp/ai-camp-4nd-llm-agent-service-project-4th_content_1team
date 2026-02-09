"""
Writer Node - 유튜브 대본 작성 에이전트
Insight Blueprint를 바탕으로 근거 기반(Evidence-Based) 대본을 생성합니다.

Architecture (Phase 1 - MVP):
    1. Draft Writer: Insight Blueprint를 따라 Hook + Chapters 생성
    2. (Phase 2) Source Binding: Claim과 Fact 연결
    3. (Phase 2) Validator: 필수 요소 검증
"""

import logging
import uuid
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

MODEL_NAME = "gpt-4o-mini"

# =============================================================================
# DATA MODELS
# =============================================================================

class Cue(BaseModel):
    type: str = Field(description="Type of cue (image, text, chart)")
    caption: str = Field(description="Description or text content for the cue")
    timing: str = Field(description="Timing instruction", default="")

class Beat(BaseModel):
    beat_id: str = Field(description="Unique ID for the beat (e.g., b1, b2)")
    purpose: str = Field(description="Purpose of this beat (evidence, narrative, transition)")
    line: str = Field(description="The actual narration script text")
    fact_references: List[str] = Field(description="List of Fact IDs cited in this line", default_factory=list)
    claims: List[str] = Field(default_factory=list)
    on_screen_cues: List[Cue] = Field(default_factory=list) # Changed from List[Dict]
    broll_ideas: List[str] = Field(default_factory=list)

class Chapter(BaseModel):
    chapter_id: str = Field(description="Chapter ID (e.g., 1)")
    title: str = Field(description="Title of the chapter")
    narration: Optional[str] = Field(description="Full narration text (optional, can be derived from beats)", default="")
    beats: List[Beat] = Field(description="List of beats making up the chapter")

class Hook(BaseModel):
    text: str = Field(description="Full text of the hook/intro")
    fact_references: List[str] = Field(default_factory=list)
    on_screen_cues: List[Cue] = Field(default_factory=list) # Changed from List[Dict]
    claims: List[str] = Field(default_factory=list)

class Closing(BaseModel):
    text: str = Field(description="Full text of the closing/outro")
    cta: str = Field(description="Call to Action text")

class Script(BaseModel):
    hook: Hook
    chapters: List[Chapter]
    closing: Closing

class QualityReport(BaseModel):
    used_fact_ids: List[str]
    unused_required_fact_ids: List[str]
    warnings_used: List[str]
    policy_checks: Dict[str, bool]

class ScriptDraft(BaseModel):
    script_draft_id: str
    topic_request_id: str
    generated_at: str
    metadata: Dict
    script: Script
    claims: List[str]
    source_map: List[Any]
    quality_report: QualityReport


async def writer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Writer Node: Insight Blueprint를 바탕으로 대본 작성
    
    Input (from state):
        - insight_pack: Insight Builder의 결과
        - news_data: News Research의 결과 (facts)
    
    Output (to state):
        - script_draft: ScriptDraft 객체
    """
    logger.info("Writer Node 시작")
    
    # Fan-in Guard: insight_pack이 비어있으면 skip (Insight Builder가 skip한 경우)
    if not state.get("insight_pack"):
        logger.info("Writer: insight 데이터 없음, skip")
        return {}
    
    # 1. 입력 데이터 추출
    insight_pack = state.get("insight_pack", {})
    news_data = state.get("news_data", {})
    facts = news_data.get("structured_facts", [])
    opinions = news_data.get("structured_opinions", [])
    channel_profile = state.get("channel_profile", {})
    
    # 1. Base Context 생성
    base_context = _build_writer_context(channel_profile, insight_pack, facts, opinions)
    
    # 2. Iterative Generation
    # (1) Intro
    logger.info("Generating Intro...")
    hook = await _generate_intro(base_context)
    
    # (2) Chapters - 병렬 생성! (속도 최적화)
    chapter_plans = insight_pack.get("story_structure", {}).get("chapters", [])
    
    if chapter_plans:
        logger.info(f"Generating {len(chapter_plans)} chapters in PARALLEL...")
        
        # 모든 챕터 동시 생성
        chapter_tasks = [
            _generate_chapter(base_context, plan, i)
            for i, plan in enumerate(chapter_plans, 1)
        ]
        chapter_results = await asyncio.gather(*chapter_tasks)
        
        # 챕터 번호 할당
        chapters = []
        for i, ch in enumerate(chapter_results, 1):
            ch.chapter_id = str(i)
            chapters.append(ch)
            logger.info(f"Chapter {i} generated: {ch.title}")
    else:
        chapters = []
        
    # (3) Outro
    logger.info("Generating Outro...")
    closing = await _generate_outro(base_context)
    
    # 3. Final Assembly
    final_script = Script(
        hook=hook,
        chapters=chapters,
        closing=closing
    )
    
    # 4. Quality Report (단순화: 전체 팩트 사용량 체크)
    all_refs = hook.fact_references + [ref for ch in chapters for beat in ch.beats for ref in beat.fact_references]
    unique_refs = list(set(all_refs))
    
    quality_report = QualityReport(
        used_fact_ids=unique_refs,
        unused_required_fact_ids=[], # TODO: Check against plan
        warnings_used=[],
        policy_checks={"iterative_mode": True}
    )
    
    script_draft = ScriptDraft(
        script_draft_id=f"scd_{uuid.uuid4().hex[:8]}",
        topic_request_id=state.get("topic_request_id"),
        generated_at=datetime.utcnow().isoformat(),
        metadata={
            "title": insight_pack.get("positioning", {}).get("thesis", "Untitled"),
            "hookType": insight_pack.get("hook_plan", {}).get("hook_type", "curiosity"),
            "estimatedDurationMin": 10
        },
        script=final_script,
        claims=[],
        source_map=[],
        quality_report=quality_report
    )
    
    logger.info(f"Writer 완료: 총 {len(chapters)}개 챕터, {len(unique_refs)}개 팩트 인용")
    
    return {
        "script_draft": script_draft.model_dump()
    }


# =============================================================================
# Helper Functions (Iterative Generation)
# =============================================================================

async def _generate_intro(context_str: str) -> Hook:
    """Step 1: Intro (Hook) 생성"""
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0.7)
    structured_llm = llm.with_structured_output(Hook)
    
    prompt = f"""
{context_str}

**TASK**: Write the HOOK (Intro) for this YouTube video.
**GOAL**: Grab attention immediately. Use the "Hook Strategy" defined in the Blueprint.
**LENGTH**: Approx 150-200 words.
**LANGUAGE**: You MUST write in Korean (한국어). Do NOT use English.
**IMPORTANT**: Even if the Blueprint/Context is in English, you MUST write the script in Korean.
**REQUIREMENTS**:
- Start with a strong hook line.
- Introduce the topic and why it matters NOW.
- Cite at least 1 FACT from the provided context.
- Fill `fact_references` with the IDs of facts used.

Generate the Hook object.
"""
    return await structured_llm.ainvoke([
        SystemMessage(content="You are an expert YouTube scriptwriter. You MUST write in Korean language."),
        HumanMessage(content=prompt)
    ])

async def _generate_chapter(context_str: str, chapter_plan: Dict, chapter_index: int) -> Chapter:
    """Step 2: Single Chapter 생성 (상세 모드)"""
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0.7)
    structured_llm = llm.with_structured_output(Chapter)
    
    # 해당 챕터용 팩트 강조
    required_facts = chapter_plan.get("required_facts", [])
    
    prompt = f"""
{context_str}

**TASK**: Write **CHAPTER {chapter_index}: {chapter_plan.get('title')}**.

**LANGUAGE**: You MUST write in Korean (한국어). Do NOT use English.
**IMPORTANT**: Even if the Blueprint/Context is in English, you MUST write the script in Korean.

**CRITICAL LENGTH REQUIREMENT**:
- This is a deep-dive section.
- Write at least **400-500 WORDS** (approx 1,000+ characters).
- Do form paragraphs, explain "Why", give examples.
- **DO NOT SUMMARIZE**. Write the full narration.

**CONTENT GUIDE**:
- Goal: {chapter_plan.get('goal')}
- Key Points: {', '.join(chapter_plan.get('key_points', []))}
- **REQUIRED EVIDENCE**: You MUST cite these facts: {required_facts}
- **OPINIONS**: Use expert quotes from the context to support this chapter.

**OUTPUT**: A single Chapter object with multiple Beats.
"""
    return await structured_llm.ainvoke([
        SystemMessage(content="You are an expert YouTube scriptwriter. You MUST write in Korean language. Write DETAILED content."),
        HumanMessage(content=prompt)
    ])

async def _generate_outro(context_str: str) -> Closing:
    """Step 3: Outro 생성"""
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0.6)
    structured_llm = llm.with_structured_output(Closing)
    
    prompt = f"""
{context_str}

**TASK**: Write the OUTRO (Closing).
**LANGUAGE**: You MUST write in Korean (한국어). Do NOT use English.
**IMPORTANT**: Even if the Blueprint/Context is in English, you MUST write the script in Korean.
**LENGTH**: Approx 100-150 words.
**REQUIREMENTS**:
- Summarize the key takeaway.
- Strong Call To Action (Subscribe, Like).
- End on a high note.

Generate the Closing object.
"""
    return await structured_llm.ainvoke([
        SystemMessage(content="You are an expert YouTube scriptwriter. You MUST write in Korean language."),
        HumanMessage(content=prompt)
    ])

def _build_writer_context(channel: Dict, insight: Dict, facts: List[Dict], opinions: List[str] = []) -> str:
    """공통 컨텍스트 조립"""
    c_str = f"## CHANNEL: {channel.get('name', 'Unknown')} ({channel.get('target_audience', 'General')})\n"
    
    i_str = f"""
## BLUEPRINT
**Thesis**: {insight.get("positioning", {}).get("thesis")}
**Hook Strategy**: {insight.get("hook_plan", {}).get("hook_type")}
"""
    # Facts & Opinions
    f_str = "\n## AVAILABLE FACTS\n"
    for f in facts[:20]: # 넉넉하게 제공
        f_str += f"- [{f.get('id')}] {f.get('content')}\n"
        
    o_str = "\n## AVAILABLE QUOTES/OPINIONS\n"
    for op in opinions[:15]:
        o_str += f"- {op}\n"
        
    return c_str + i_str + f_str + o_str
