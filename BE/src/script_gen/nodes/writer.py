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
# 공통 시스템 프롬프트 (Hook / Chapter / Outro 공유)
# =============================================================================

_WRITER_RULES = """★ Part 1 — CHANNEL VOICE (최우선):
- CHANNEL 섹션에 톤앤매너(tone_manner)와 말투 샘플(tone_samples)이 있으면,
  대본 전체의 말투와 톤을 해당 스타일로 작성하세요. 이것이 최우선 규칙입니다.
- tone_samples는 말투 참고용입니다. 샘플 문장을 대본에 그대로 복사하지 마세요.
- hit_patterns(잘 먹히는 패턴)은 적극 따르고, low_patterns(피해야 할 패턴)은 피하세요.
- content_structures(영상 구조)가 있으면 해당 구조를 참고하세요.
- 톤앤매너 정보가 없는 경우에만 기본적인 유튜브 대화체로 작성하세요.

■ Part 2 -- FACT LOCK (수치/데이터 할루시네이션 방지):
- 수치, 데이터, 고유명사, 인용문은 반드시 AVAILABLE FACTS에서만 가져오세요.
- 당신의 학습 데이터에서 알고 있는 벤치마크 점수, 토큰 수, 날짜, 금액 등을 절대 추가하지 마세요.
- 팩트에 구체적 수치가 없으면, 일반적 표현으로 서술하세요.
- fact_references에는 실제로 인용한 Fact의 ID만 넣으세요.

※ Part 3 -- STORYTELLING FREEDOM:
- 비유/예시("마치 ~처럼"), 수사적 질문, 감정 표현, 해석("이게 중요한 이유는"),
  전환 장치("근데 여기서") 등은 자유롭게 사용할 수 있습니다.
- 단, 이러한 표현에 구체적 수치나 데이터를 포함하면 안 됩니다.
- 팩트를 나열식으로 쭉 이어쓰지 말고, 스토리 흐름 속에 자연스럽게 녹이세요.
- 같은 전환 표현을 반복하지 마세요. 도입/전환/강조 표현은 매번 다르게 쓰세요.

[금지] 의미 왜곡 금지:
- 팩트 원문의 핵심 의미를 확대, 축소, 왜곡하지 마세요.
- 팩트 원문에 없는 키워드, 개념, 분야를 새로 만들어 넣지 마세요.
- 기사에서 실제로 언급하지 않은 사실을 해당 기사의 인용으로 표기하지 마세요.

[참고] BAD/GOOD 예시:
[X] BAD (수치 날조): 'ARC-AGI 2 벤치마크에서 68.8%를 기록' -> 팩트에 없는 수치
[O] GOOD: '다양한 벤치마크에서 높은 성능을 기록' -> 구체적 수치 없이 서술
[X] BAD (수치 날조): '1백만 토큰 컨텍스트 창을 지원' -> 팩트에 없는 구체적 수치
[O] GOOD: '더 큰 컨텍스트 창을 통해 복잡한 작업 처리 가능' -> 팩트 원문 그대로
[X] BAD (키워드 날조): '생물테러 방어책 연구' -> '국방 분야 통합' -> 원문에 없는 키워드
[O] GOOD: '생물테러 위험을 줄이기 위한 방어책을 개발' -> 원문 충실 반영
[X] BAD (팩트 나열식): 'A가 발표했습니다(1). B가 향상됐습니다(2). C도 출시됐습니다(3).' -> 뉴스 기사
[O] GOOD (구조): [도입/배경] -> 팩트(1)을 맥락 속에 배치 -> [해석/의미] -> 팩트(2)로 자연스러운 전환"""

def _build_system_prompt(extra: str = "") -> str:
    """Writer 공통 시스템 프롬프트 생성 (extra: 'Write DETAILED content.' 등 추가 지시)"""
    base = (
        "You are an expert YouTube scriptwriter. You MUST write in Korean language."
        " You write scripts that sound like a real YouTuber talking, NOT a news anchor reading."
    )
    if extra:
        base += f" {extra}"
    return f"{base}\n{_WRITER_RULES}"


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
    
    # (2) Chapters — 순차 생성 (도입부 다양성 + 팩트 격리 + Self-Check)
    chapter_plans = insight_pack.get("story_structure", {}).get("chapters", [])
    
    if chapter_plans:
        logger.info(f"Generating {len(chapter_plans)} chapters SEQUENTIALLY...")
        
        all_chapter_facts = [
            set(plan.get("required_facts", [])) for plan in chapter_plans
        ]
        
        chapters = []
        previous_openings = []   # 이전 챕터 도입 문장 (패턴 반복 방지)
        used_facts_summary = []  # 이전 챕터에서 사용된 팩트 요약
        
        for i, plan in enumerate(chapter_plans, 1):
            # 이 챕터의 배정 팩트만 포함된 컨텍스트 생성
            chapter_context = _build_writer_context(
                channel_profile, insight_pack, facts, opinions,
                filter_fact_ids=all_chapter_facts[i - 1],
                used_facts_summary=used_facts_summary if used_facts_summary else None
            )
            
            ch = await _generate_chapter(
                chapter_context, plan, i,
                previous_openings=previous_openings
            )
            ch.chapter_id = str(i)
            ch.narration = "\n".join(beat.line for beat in ch.beats)
            
            # Self-Check: 누락 팩트 확인 → 1회 재시도
            cited_ids = set(ref for beat in ch.beats for ref in beat.fact_references)
            required_ids = all_chapter_facts[i - 1]
            missing = required_ids - cited_ids
            if missing:
                logger.warning(f"Ch{i}: 미인용 팩트 {len(missing)}개 → 재생성")
                ch = await _generate_chapter(
                    chapter_context, plan, i,
                    previous_openings=previous_openings,
                    must_include_facts=list(missing)
                )
                ch.chapter_id = str(i)
                ch.narration = "\n".join(beat.line for beat in ch.beats)
                cited_ids = set(ref for beat in ch.beats for ref in beat.fact_references)
            
            # 이전 챕터 도입 문장 수집
            if ch.beats:
                first_line = ch.beats[0].line[:60]
                previous_openings.append(f"Ch{i}: \"{first_line}\"")
            
            # 이전 챕터 사용 팩트 요약 수집 + 다음 챕터에서 제외
            for ref_id in cited_ids:
                fact_obj = next((f for f in facts if f.get("id") == ref_id), None)
                if fact_obj:
                    preview = fact_obj.get("content", "")[:50]
                    used_facts_summary.append(f"\"{preview}\" (Ch{i}에서 사용됨)")
                
                # 이미 인용된 팩트를 다음 챕터 배정에서 제거 (코드 레벨 중복 방지)
                for future_idx in range(i, len(all_chapter_facts)):
                    all_chapter_facts[future_idx].discard(ref_id)
            
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


async def writer_rewrite_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifier 피드백 루프: critical 이슈가 있는 Beat만 재생성
    
    Input: script_draft, verifier_output, news_data, channel_profile, insight_pack
    Output: 수정된 script_draft + verifier_retry_count 증가
    """
    logger.info("Writer Rewrite Node 시작")
    
    # 1. 입력 데이터 추출
    script_draft = state.get("script_draft", {})
    verifier_output = state.get("verifier_output", {})
    news_data = state.get("news_data", {})
    channel_profile = state.get("channel_profile", {})
    insight_pack = state.get("insight_pack", {})
    facts = news_data.get("structured_facts", [])
    opinions = news_data.get("structured_opinions", [])
    retry_count = state.get("verifier_retry_count", 0)
    
    # 2. Critical 이슈 Beat 수집
    report = verifier_output.get("verification_report", {})
    issues = report.get("issues", [])
    critical_issues = [i for i in issues if i.get("severity") == "critical"]
    
    if not critical_issues:
        logger.info("Critical 이슈 없음, 스킵")
        return {"verifier_retry_count": retry_count + 1}
    
    # Beat ID별 이슈 그룹핑
    beat_issues: Dict[str, List[Dict]] = {}
    for issue in critical_issues:
        bid = issue.get("beat_id", "")
        if bid not in beat_issues:
            beat_issues[bid] = []
        beat_issues[bid].append(issue)
    
    logger.info(f"Critical Beat {len(beat_issues)}개 재생성 (retry {retry_count + 1}/2)")
    
    # 3. 컨텍스트 조립 (원래 Writer와 동일)
    base_context = _build_writer_context(channel_profile, insight_pack, facts, opinions)
    
    # 4-A. Hook 재생성 (hook beat_id가 이슈에 포함된 경우)
    script = script_draft.get("script", {})
    
    if "hook" in beat_issues:
        feedback = "\n".join([
            f"- [{i.get('issue_type')}] {i.get('description')}"
            for i in beat_issues["hook"]
        ])
        try:
            hook_beat = {
                "beat_id": "hook",
                "purpose": "Hook/Intro",
                "line": script.get("hook", {}).get("text", "") if isinstance(script.get("hook"), dict) else script.get("hook", ""),
            }
            new_hook = await _rewrite_single_beat(
                base_context, hook_beat, "Hook (인트로)", feedback, facts
            )
            # Hook 텍스트 교체
            if isinstance(script.get("hook"), dict):
                script["hook"]["text"] = new_hook.line
            else:
                script["hook"] = new_hook.line
            logger.info("Hook 재생성 완료")
        except Exception as e:
            logger.warning(f"Hook 재생성 실패: {e}")
    
    # 4-B. 챕터 Beat 재생성
    chapters = script.get("chapters", [])
    
    for ch_idx, chapter in enumerate(chapters):
        beats = chapter.get("beats", [])
        for beat_idx, beat in enumerate(beats):
            bid = beat.get("beat_id", "")
            if bid not in beat_issues:
                continue
            
            feedback = "\n".join([
                f"- [{i.get('issue_type')}] {i.get('description')}"
                for i in beat_issues[bid]
            ])
            
            try:
                new_beat = await _rewrite_single_beat(
                    base_context, beat, chapter.get("title", ""), feedback, facts
                )
                chapters[ch_idx]["beats"][beat_idx] = new_beat.model_dump()
                
                chapters[ch_idx]["narration"] = "\n".join(
                    b.get("line", "") if isinstance(b, dict) else b.line
                    for b in chapters[ch_idx]["beats"]
                )
                logger.info(f"Beat '{bid}' 재생성 완료")
            except Exception as e:
                logger.warning(f"Beat '{bid}' 재생성 실패: {e}")
    
    # 5. script_draft 업데이트
    script_draft["script"]["chapters"] = chapters
    
    return {
        "script_draft": script_draft,
        "verifier_retry_count": retry_count + 1
    }


async def _rewrite_single_beat(
    context_str: str, 
    old_beat: Dict, 
    chapter_title: str,
    feedback: str,
    facts: List[Dict]
) -> Beat:
    """Verifier 피드백을 반영해 단일 Beat 재생성"""
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0.3)
    structured_llm = llm.with_structured_output(Beat)
    
    # 인용 가능한 팩트 목록
    fact_list = "\n".join([
        f"- [{f.get('id')}] {f.get('content')}" for f in facts[:20]
    ])
    
    prompt = f"""
{context_str}

**TASK**: 아래 Beat를 수정해주세요. Verifier가 발견한 문제를 반영해야 합니다.

**챕터**: {chapter_title}
**원래 Beat**:
- ID: {old_beat.get('beat_id')}
- 목적: {old_beat.get('purpose')}
- 원문: {old_beat.get('line')}

**Verifier 피드백 (반드시 수정)**:
{feedback}

**수정 규칙**:
- Beat ID와 purpose는 유지하세요.
- 의미 왜곡(semantic_distortion)이면: 팩트 원문에 충실하게 다시 쓰세요.
- 존재하지 않는 팩트 ID(invalid_fact_id)면: 해당 인용을 제거하거나 올바른 팩트로 교체하세요.
- CHANNEL 섹션의 말투 스타일을 유지하세요.
- 수치는 반드시 아래 팩트 목록에서만 가져오세요.

**인용 가능한 팩트**:
{fact_list}

**LANGUAGE**: 한국어로 작성하세요.
"""
    return await structured_llm.ainvoke([
        SystemMessage(content=_build_system_prompt("Fix the beat based on verifier feedback.")),
        HumanMessage(content=prompt)
    ])


# =============================================================================
# Helper Functions (Iterative Generation)
# =============================================================================

async def _generate_intro(context_str: str) -> Hook:
    """Step 1: Intro (Hook) 생성"""
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0.6)
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
- Cite exactly 1 FACT (가장 충격적인 것 1개만). 여러 팩트를 나열하지 마세요.
- **INLINE CITATION**: When citing a fact, place its circle number (①②③) at the END of the sentence.
- Fill `fact_references` with the IDs of facts used.
**STYLE**:
- 뉴스 리포트 톤으로 시작하지 마라 (❌ "최근 ~가 발표되었습니다" 식의 도입 금지).
- CHANNEL 섹션의 말투 스타일(tone_samples)로 작성하라.
- 팩트는 자연스러운 흐름 속에 녹여라.

Generate the Hook object.
"""
    for attempt in range(3):
        try:
            return await structured_llm.ainvoke([
                SystemMessage(content=_build_system_prompt()),
                HumanMessage(content=prompt)
            ])
        except Exception as e:
            logger.warning(f"Hook 생성 실패 (시도 {attempt+1}/3): {e}")
            if attempt == 2:
                raise
            await asyncio.sleep(2)

async def _generate_chapter(context_str: str, chapter_plan: Dict, chapter_index: int,
                           previous_openings: List[str] = None,
                           must_include_facts: List[str] = None) -> Chapter:
    """Step 2: Single Chapter 생성 (팩트 격리 + 도입부 다양성 + Self-Check)"""
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0.4)
    structured_llm = llm.with_structured_output(Chapter)
    
    required_facts = chapter_plan.get("required_facts", [])
    
    # 이전 챕터 도입 문장 (같은 패턴 반복 방지)
    opening_guide = ""
    if previous_openings:
        opening_guide = "\n**이전 챕터 도입문 (같은 패턴으로 시작하지 마세요)**:\n"
        for op in previous_openings:
            opening_guide += f"- {op}\n"
        opening_guide += "→ 위와 **완전히 다른 방식**으로 이 챕터를 시작하세요.\n"
    
    # Self-Check 재시도 시 누락 팩트 강조
    must_include_str = ""
    if must_include_facts:
        must_include_str = f"\n- ⚠️ **반드시 포함해야 하는 미인용 팩트**: {must_include_facts} — 이 팩트들이 빠지면 실패입니다."
    
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
- **REQUIRED EVIDENCE**: You MUST cite ALL of these facts: {required_facts}{must_include_str}
- **INLINE CITATION**: When citing a fact, place its circle number (①②③) at the END of that sentence.
- **OPINIONS**: Use expert quotes from the context to support this chapter. OPINIONS도 반드시 출처 번호를 붙이세요.
- **다출처 인용**: 가능한 한 다양한 출처 번호의 팩트를 인용하세요.

**NARRATION STYLE**:
- **도입부**: 이 챕터의 goal({chapter_plan.get('goal')})에서 자연스럽게 시작하세요.
{opening_guide}- 이전 챕터에서 자연스럽게 이어지는 것처럼 쓰세요. 갑자기 새로 시작하는 느낌을 주지 마세요.
- 팩트를 나열식으로 쭉 이어쓰지 마라. 스토리 흐름 속에 자연스럽게 녹여라.
- "~했습니다. ~했습니다. ~했습니다." 같은 반복 종결어미 패턴을 피하라.
- CHANNEL 섹션의 말투 **어미·어감**을 유지하되, 아래 표현은 이 챕터에서 **사용 금지**:
  ❌ "자 여러분", "자 그러면", "자 이제", "자," — 호칭/전환 표현 금지
  ❌ "안녕하세요", "여러분" 으로 시작하는 문장 금지
  ❌ 이전 챕터와 동일한 첫 단어/패턴으로 시작 금지
  ❌ "댓글로 공유", "어떻게 생각하세요?", "구독과 좋아요" 등 시청자 참여 유도(CTA)는 챕터 본문에서 금지. CTA는 아웃트로에서만 사용.

**OUTPUT**: A single Chapter object with multiple Beats.
"""
    for attempt in range(3):
        try:
            return await structured_llm.ainvoke([
                SystemMessage(content=_build_system_prompt("Write DETAILED content.")),
                HumanMessage(content=prompt)
            ])
        except Exception as e:
            logger.warning(f"Chapter {chapter_index} 생성 실패 (시도 {attempt+1}/3): {e}")
            if attempt == 2:
                raise
            await asyncio.sleep(2)

async def _generate_outro(context_str: str) -> Closing:
    """Step 3: Outro 생성"""
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0.5)
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
- 새로운 팩트를 인용하지 마세요. 영상 전체의 핵심 메시지만 요약하세요.
**STYLE**:
- 뉴스 마무리("이상 ~였습니다") 톤이 아닌, CHANNEL 섹션의 말투 스타일로 마무리하라.

Generate the Closing object.
"""
    for attempt in range(3):
        try:
            return await structured_llm.ainvoke([
                SystemMessage(content=_build_system_prompt()),
                HumanMessage(content=prompt)
            ])
        except Exception as e:
            logger.warning(f"Outro 생성 실패 (시도 {attempt+1}/3): {e}")
            if attempt == 2:
                raise
            await asyncio.sleep(2)

CIRCLE_NUMBERS = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩",
                  "⑪", "⑫", "⑬", "⑭", "⑮", "⑯", "⑰", "⑱", "⑲", "⑳"]

def _build_writer_context(channel: Dict, insight: Dict, facts: List[Dict], opinions: List[str] = [],
                          filter_fact_ids: set = None, used_facts_summary: List[str] = None) -> str:
    """공통 컨텍스트 조립 (기사 기준 인라인 출처 번호 포함, 챕터별 팩트 필터링 지원)"""
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
        c_str += "\n### 말투 가이드 (이 채널의 개성 — 중요!)\n"
        c_str += "아래는 이 크리에이터의 실제 말투 샘플입니다. **말투 DNA**를 파악하세요.\n\n"
        c_str += "**[적용 규칙 — 반드시 준수]**:\n"
        c_str += "1. **어미 패턴**(~거든요, ~잖아요, ~인데요 등) → 대본 전체에 **적극 반영**하세요. 이것이 채널 개성의 핵심입니다.\n"
        c_str += "2. **호칭/인사**(자 여러분, 안녕하세요, 여러분 등) → **Hook(인트로)에서 최대 1회만**. 챕터 본문에서는 사용 금지.\n"
        c_str += "3. **전환 표현**(자 그러면, 자 이제, 근데 여기서 등) → **영상 전체에서 최대 2회**. 나머지는 다른 전환 방식 사용.\n"
        c_str += "4. 아래 문장을 **통째로 복사하지 마세요**. 문장의 **끝(어미)과 어감**만 흡수하세요.\n"
        c_str += "5. 같은 표현을 2회 이상 반복하면 **실패**입니다.\n\n"
        c_str += "**참고 문장** (어미·어감만 참고):\n"
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
    # 전체 목차 추가 (챕터 간 맥락 파악용 — 내용 중복/흐름 단절 방지)
    chapters_outline = insight.get("story_structure", {}).get("chapters", [])
    if chapters_outline:
        i_str += "\n**전체 목차**:\n"
        for idx, ch in enumerate(chapters_outline, 1):
            i_str += f"  {idx}. {ch.get('title', '')} -- {ch.get('goal', '')}\n"
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
        "- ⚠️ 아래 나열된 팩트를 **전부** 인용하세요. 하나라도 빠지면 실패입니다.\n"
    )
    # 이전 챕터에서 사용된 팩트 요약 (반복 방지)
    if used_facts_summary:
        f_str += "\n### ⚠️ 이전 챕터에서 이미 다뤄진 내용 (반복 금지)\n"
        for s in used_facts_summary:
            f_str += f"- {s}\n"
        f_str += "\n"
    for i, f in enumerate(facts):
        # 확정된 source_index를 우선 사용
        art_idx = f.get("source_index")
        if art_idx is None:
            source_indices = f.get("source_indices", [])
            art_idx = source_indices[0] if source_indices and isinstance(source_indices[0], int) else i
        
        if art_idx not in article_idx_to_marker:
            marker = CIRCLE_NUMBERS[next_marker_idx] if next_marker_idx < len(CIRCLE_NUMBERS) else f"[{next_marker_idx+1}]"
            article_idx_to_marker[art_idx] = marker
            article_idx_to_source[art_idx] = f.get("source_name", "")
            next_marker_idx += 1
        
        # 챕터별 팩트 필터링: filter_fact_ids가 지정된 경우 해당 팩트만 표시
        if filter_fact_ids is not None and f.get("id") not in filter_fact_ids:
            continue
        
        marker = article_idx_to_marker[art_idx]
        source_label = f.get("source_name", "")
        f_str += f"- {marker} [{f.get('id')}] ({source_label}) {f.get('content')}\n"
        
    o_str = "\n## AVAILABLE QUOTES/OPINIONS\n"
    o_str += (
        "**인용 규칙**: 아래 의견/주장을 인용할 때도 반드시 출처 번호를 문장 끝에 붙이세요.\n"
    )
    for op in opinions[:15]:
        # opinions 형식: "[출처명] 내용" → 출처명으로 기사 번호 매핑
        op_source = ""
        if op.startswith("[") and "]" in op:
            op_source = op[1:op.index("]")]
        # article_idx_to_source에서 출처명 → 번호 역매핑
        op_marker = ""
        for art_idx, src_name in article_idx_to_source.items():
            if src_name and op_source and (src_name in op_source or op_source in src_name):
                op_marker = article_idx_to_marker.get(art_idx, "")
                break
        o_str += f"- {op_marker} {op}\n"
        
    return c_str + i_str + f_str + o_str
