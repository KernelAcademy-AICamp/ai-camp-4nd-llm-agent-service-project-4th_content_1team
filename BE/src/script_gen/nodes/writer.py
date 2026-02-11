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
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

MODEL_NAME = "gpt-4o"

# =============================================================================
# DATA MODELS
# =============================================================================

class Cue(BaseModel):
    type: Literal["text", "image", "table", "chart", "broll", "screenshot"] = Field(description="Type of cue")
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
        
        # 챕터별 배정 팩트 수집 → 다른 챕터의 팩트를 excluded로 전달 (중복 방지)
        all_chapter_facts = [
            set(plan.get("required_facts", [])) for plan in chapter_plans
        ]
        
        chapter_tasks = []
        for i, plan in enumerate(chapter_plans, 1):
            # 이 챕터 제외, 나머지 챕터의 팩트를 excluded로
            excluded = set()
            for j, other_facts in enumerate(all_chapter_facts):
                if j != i - 1:
                    excluded |= other_facts
            chapter_tasks.append(
                _generate_chapter(base_context, plan, i, list(excluded))
            )
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
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0.3)
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
- **INLINE CITATION**: When citing a fact, place its circle number (①②③) at the END of the sentence.
- Fill `fact_references` with the IDs of facts used.

Generate the Hook object.
"""
    return await structured_llm.ainvoke([
        SystemMessage(content="You are an expert YouTube scriptwriter. You MUST write in Korean language.\n채널의 톤앤매너와 말투 샘플이 CHANNEL 섹션에 있으면, 반드시 해당 스타일을 반영하여 작성하세요.\n\n🔒 닫힌 책(CLOSED-BOOK) 모드 — 최우선 규칙:\n- 당신은 자체 지식이 없습니다. AVAILABLE FACTS가 당신의 유일한 정보원입니다.\n- AVAILABLE FACTS에 명시적으로 적힌 정보만 사용할 수 있습니다.\n- 당신의 학습 데이터에서 알고 있는 수치, 벤치마크 점수, 토큰 수, 날짜, 금액 등을 절대 추가하지 마세요.\n- 팩트에 구체적 수치가 없으면, 일반적 표현으로 서술하세요.\n- fact_references에는 실제로 인용한 Fact의 ID만 넣으세요.\n\n🚫 의미 왜곡 금지:\n- 팩트 원문의 핵심 의미를 확대, 축소, 왜곡하지 마세요.\n- 팩트 원문에 없는 키워드, 개념, 분야를 새로 만들어 넣지 마세요.\n- 기사에서 실제로 언급하지 않은 사실을 해당 기사의 인용으로 표기하지 마세요.\n\n📝 BAD/GOOD 예시 (반드시 참고):\n❌ BAD: 'ARC-AGI 2 벤치마크에서 68.8%를 기록' → 팩트에 없는 수치 날조\n✅ GOOD: '다양한 벤치마크에서 높은 성능을 기록' → 구체적 수치 없이 서술\n❌ BAD: '1백만 토큰 컨텍스트 창을 지원' → 팩트에 없는 구체적 수치\n✅ GOOD: '더 큰 컨텍스트 창을 통해 복잡한 작업 처리 가능' → 팩트 원문 그대로\n❌ BAD: '생물테러 방어책 연구' → '국방 분야 통합' → 원문에 없는 키워드 날조\n✅ GOOD: '생물테러 위험을 줄이기 위한 방어책을 개발' → 원문 충실 반영"),
        HumanMessage(content=prompt)
    ])

async def _generate_chapter(context_str: str, chapter_plan: Dict, chapter_index: int, excluded_facts: List[str] = []) -> Chapter:
    """Step 2: Single Chapter 생성 (상세 모드, 팩트 중복 방지)"""
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0.3)
    structured_llm = llm.with_structured_output(Chapter)
    
    # 해당 챕터용 팩트 강조
    required_facts = chapter_plan.get("required_facts", [])
    
    # 다른 챕터에 배정된 팩트 → 사용 금지 목록
    excluded_str = ""
    if excluded_facts:
        excluded_str = f"\n- **DO NOT USE these facts** (they belong to other chapters): {excluded_facts}"
    
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
- **REQUIRED EVIDENCE**: You MUST cite these facts: {required_facts}{excluded_str}
- **INLINE CITATION**: When citing a fact, place its circle number (①②③) at the END of that sentence.
- **OPINIONS**: Use expert quotes from the context to support this chapter.

**OUTPUT**: A single Chapter object with multiple Beats.
"""
    return await structured_llm.ainvoke([
        SystemMessage(content="You are an expert YouTube scriptwriter. You MUST write in Korean language. Write DETAILED content.\n채널의 톤앤매너와 말투 샘플이 CHANNEL 섹션에 있으면, 반드시 해당 스타일을 반영하여 작성하세요.\n\n🔒 닫힌 책(CLOSED-BOOK) 모드 — 최우선 규칙:\n- 당신은 자체 지식이 없습니다. AVAILABLE FACTS가 당신의 유일한 정보원입니다.\n- AVAILABLE FACTS에 명시적으로 적힌 정보만 사용할 수 있습니다.\n- 당신의 학습 데이터에서 알고 있는 수치, 벤치마크 점수, 토큰 수, 날짜, 금액 등을 절대 추가하지 마세요.\n- 팩트에 구체적 수치가 없으면, 일반적 표현으로 서술하세요.\n- fact_references에는 실제로 인용한 Fact의 ID만 넣으세요.\n\n🚫 의미 왜곡 금지:\n- 팩트 원문의 핵심 의미를 확대, 축소, 왜곡하지 마세요.\n- 팩트 원문에 없는 키워드, 개념, 분야를 새로 만들어 넣지 마세요.\n- 기사에서 실제로 언급하지 않은 사실을 해당 기사의 인용으로 표기하지 마세요.\n\n📝 BAD/GOOD 예시 (반드시 참고):\n❌ BAD: 'ARC-AGI 2 벤치마크에서 68.8%를 기록' → 팩트에 없는 수치 날조\n✅ GOOD: '다양한 벤치마크에서 높은 성능을 기록' → 구체적 수치 없이 서술\n❌ BAD: '1백만 토큰 컨텍스트 창을 지원' → 팩트에 없는 구체적 수치\n✅ GOOD: '더 큰 컨텍스트 창을 통해 복잡한 작업 처리 가능' → 팩트 원문 그대로\n❌ BAD: '생물테러 방어책 연구' → '국방 분야 통합' → 원문에 없는 키워드 날조\n✅ GOOD: '생물테러 위험을 줄이기 위한 방어책을 개발' → 원문 충실 반영"),
        HumanMessage(content=prompt)
    ])

async def _generate_outro(context_str: str) -> Closing:
    """Step 3: Outro 생성"""
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0.3)
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
        SystemMessage(content="You are an expert YouTube scriptwriter. You MUST write in Korean language.\n채널의 톤앤매너와 말투 샘플이 CHANNEL 섹션에 있으면, 반드시 해당 스타일을 반영하여 작성하세요.\n\n🔒 닫힌 책(CLOSED-BOOK) 모드 — 최우선 규칙:\n- 당신은 자체 지식이 없습니다. AVAILABLE FACTS가 당신의 유일한 정보원입니다.\n- AVAILABLE FACTS에 명시적으로 적힌 정보만 사용할 수 있습니다.\n- 당신의 학습 데이터에서 알고 있는 수치, 벤치마크 점수, 토큰 수, 날짜, 금액 등을 절대 추가하지 마세요.\n- 팩트에 구체적 수치가 없으면, 일반적 표현으로 서술하세요.\n- fact_references에는 실제로 인용한 Fact의 ID만 넣으세요.\n\n🚫 의미 왜곡 금지:\n- 팩트 원문의 핵심 의미를 확대, 축소, 왜곡하지 마세요.\n- 팩트 원문에 없는 키워드, 개념, 분야를 새로 만들어 넣지 마세요.\n\n📝 BAD/GOOD 예시:\n❌ BAD: 'ARC-AGI 2에서 68.8%' → 팩트에 없는 수치 날조\n✅ GOOD: '높은 성능을 기록' → 일반적 표현\n❌ BAD: '방어책 연구' → '국방 통합' → 키워드 날조\n✅ GOOD: '방어책을 개발' → 원문 반영"),
        HumanMessage(content=prompt)
    ])

CIRCLE_NUMBERS = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩",
                  "⑪", "⑫", "⑬", "⑭", "⑮", "⑯", "⑰", "⑱", "⑲", "⑳"]

def _build_writer_context(channel: Dict, insight: Dict, facts: List[Dict], opinions: List[str] = []) -> str:
    """공통 컨텍스트 조립 (기사 기준 인라인 출처 번호 포함)"""
    c_str = f"## CHANNEL: {channel.get('name', 'Unknown')}\n"
    c_str += f"- 타겟 시청자: {channel.get('target_audience', '일반 시청자')}\n"
    
    # 페르소나 정보
    if channel.get("persona_summary"):
        c_str += f"- 채널 정체성: {channel['persona_summary']}\n"
    if channel.get("content_style"):
        c_str += f"- 콘텐츠 스타일: {channel['content_style']}\n"
    if channel.get("differentiator"):
        c_str += f"- 차별화 포인트: {channel['differentiator']}\n"
    if channel.get("audience_needs"):
        c_str += f"- 시청자 니즈: {channel['audience_needs']}\n"
    if channel.get("average_duration"):
        c_str += f"- 적정 영상 길이: {channel['average_duration']}\n"
    
    # 톤/말투 (자막 분석 기반)
    if channel.get("tone_manner"):
        c_str += f"\n### 톤앤매너\n{channel['tone_manner']}\n"
    if channel.get("tone_samples"):
        c_str += f"\n### 말투 샘플 (이 스타일을 반영하세요)\n"
        for sample in channel["tone_samples"][:5]:
            c_str += f"- \"{sample}\"\n"
    
    # 성공 공식/패턴
    if channel.get("success_formula"):
        c_str += f"\n### 성공 공식\n{channel['success_formula']}\n"
    
    # 히트/저조 패턴 (DO/DON'T 가이드)
    if channel.get("hit_patterns"):
        c_str += f"\n### ✅ 이 채널에서 잘 먹히는 패턴 (따라하세요)\n"
        for p in channel["hit_patterns"][:5]:
            c_str += f"- {p}\n"
    if channel.get("low_patterns"):
        c_str += f"\n### ❌ 피해야 할 패턴 (하지 마세요)\n"
        for p in channel["low_patterns"][:5]:
            c_str += f"- {p}\n"
    
    # 콘텐츠 구조 패턴
    if channel.get("content_structures"):
        c_str += f"\n### 영상 유형별 구조 (참고)\n"
        for vtype, structure in channel["content_structures"].items():
            c_str += f"- {vtype}: {structure}\n"
    
    i_str = f"""
## BLUEPRINT
**Thesis**: {insight.get("positioning", {}).get("thesis")}
**Hook Strategy**: {insight.get("hook_plan", {}).get("hook_type")}
"""
    # 기사(article) 기준으로 번호 매핑: source_index(확정) → 기사 번호
    article_idx_to_marker: Dict[int, str] = {}
    article_idx_to_source: Dict[int, str] = {}
    next_marker_idx = 0

    f_str = "\n## AVAILABLE FACTS\n"
    f_str += (
        "**인용 규칙 (필수)**:\n"
        "- 번호는 '기사(출처)' 단위입니다. 같은 기사에서 나온 팩트는 같은 번호를 사용합니다.\n"
        "- 팩트를 인용할 때 반드시 **해당 기사의 번호**를 문장 끝에 붙이세요.\n"
        "- 예시: ①번 기사의 팩트면 → '불만이 70% 감소했습니다①'\n"
        "- 같은 기사의 다른 팩트도 같은 번호를 사용합니다.\n"
        "- ⚠️ **모든 출처를 최소 1회 이상 인용하세요.** 특정 기사에 편중되지 않도록 골고루 인용합니다.\n"
    )
    for i, f in enumerate(facts):
        # 확정된 source_index를 우선 사용 (news_research에서 하드코딩)
        art_idx = f.get("source_index")
        if art_idx is None:
            # 호환: 기존 source_indices fallback
            source_indices = f.get("source_indices", [])
            art_idx = source_indices[0] if source_indices and isinstance(source_indices[0], int) else i
        
        if art_idx not in article_idx_to_marker:
            marker = CIRCLE_NUMBERS[next_marker_idx] if next_marker_idx < len(CIRCLE_NUMBERS) else f"[{next_marker_idx+1}]"
            article_idx_to_marker[art_idx] = marker
            article_idx_to_source[art_idx] = f.get("source_name", "")
            next_marker_idx += 1
        
        marker = article_idx_to_marker[art_idx]
        source_label = f.get("source_name", "")
        f_str += f"- {marker} [{f.get('id')}] ({source_label}) {f.get('content')}\n"
        
    o_str = "\n## AVAILABLE QUOTES/OPINIONS\n"
    for op in opinions[:15]:
        o_str += f"- {op}\n"
        
    return c_str + i_str + f_str + o_str
