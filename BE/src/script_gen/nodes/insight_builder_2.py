"""
Insight Builder Node v2 - Claude Sonnet 4.5 버전
insight_builder.py 와 동일한 로직, LLM만 교체 (GPT-4o → Claude Sonnet 4.5)

A/B 테스트용: graph.py에서 import를 바꿔 두 버전 비교
  - v1: from src.script_gen.nodes.insight_builder import insight_builder_node
  - v2: from src.script_gen.nodes.insight_builder_2 import insight_builder_node
"""

import logging
import uuid
import json
from typing import Dict, Any, List, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from src.script_gen.schemas.insight import InsightPack
from src.script_gen.schemas.competitor import CompetitorAnalysisResult

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

MODEL_NAME = "claude-sonnet-4-5"


def insight_builder_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("🤖 Insight Builder v2 (Claude Sonnet 4.5) 시작")

    # Fan-in Guard
    if state.get("competitor_data") is None:
        logger.info("🤖 Insight Builder v2: competitor 분석 대기 중, skip")
        return {}

    topic = state.get("topic", "Unknown Topic")
    channel_profile = state.get("channel_profile", {})

    news_data = state.get("news_data", {})
    facts = news_data.get("structured_facts", [])

    raw_comp_data = state.get("competitor_data", {})
    competitor_result = _parse_competitor_data(raw_comp_data)

    logger.info(f"🤖 [입력] 주제: {topic}")
    logger.info(f"🤖 [입력] 팩트 수: {len(facts)}개")
    logger.info(f"🤖 [입력] 경쟁사 데이터 존재: {competitor_result is not None}")

    context_str = _build_context_string(topic, channel_profile, facts, competitor_result)

    # --- Pass 1: Draft Generation ---
    logger.info("🤖 Pass 1: Creating Strategy Draft (Claude)...")
    draft_pack = None
    max_retries = 3

    for attempt in range(max_retries):
        try:
            draft_pack = _generate_draft(context_str)
            break
        except Exception as e:
            logger.warning(f"🤖 Draft 생성 실패 (시도 {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise

    logger.info(f"🤖 [Pass1 결과] thesis: {draft_pack.positioning.thesis}")

    # --- Pass 2: Critic & Repair ---
    logger.info("🤖 Pass 2: Critiquing and Refining (Claude)...")
    final_pack = None

    for attempt in range(max_retries):
        try:
            final_pack = _critique_and_refine(context_str, draft_pack)
            break
        except Exception as e:
            logger.warning(f"🤖 Refine 실패 (시도 {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise

    # --- Finalize ---
    if not final_pack.insight_pack_id:
        final_pack.insight_pack_id = f"ins_{uuid.uuid4().hex[:8]}"

    # =========================================================
    # 🤖 최종 결과 로그
    # =========================================================
    pos = final_pack.positioning
    hook = final_pack.hook_plan
    chapters = final_pack.story_structure.chapters
    diffs = final_pack.differentiators
    wi = final_pack.writer_instructions

    logger.info("🤖 ==================== Insight Builder v2 결과 ====================")
    logger.info(f"🤖 [포지셔닝] thesis: {pos.thesis}")
    logger.info(f"🤖 [포지셔닝] promise: {pos.one_sentence_promise}")
    logger.info(f"🤖 [포지셔닝] 타겟: {pos.who_is_this_for}")
    logger.info(f"🤖 [포지셔닝] 시청 후 이득: {pos.what_they_will_get}")

    logger.info(f"🤖 [훅 플랜] 유형: {hook.hook_type}")
    for hs in hook.hook_scripts:
        logger.info(f"🤖 [훅 스크립트 {hs.id}] {hs.text[:80]}... (팩트: {hs.uses_fact_ids})")
    thumb = hook.thumbnail_angle
    logger.info(f"🤖 [썸네일] 컨셉: {thumb.concept}")
    logger.info(f"🤖 [썸네일] 문구 후보: {thumb.copy_candidates}")

    logger.info(f"🤖 [챕터 구성] 총 {len(chapters)}개")
    for ch in chapters:
        logger.info(
            f"🤖   챕터 [{ch.chapter_id}] '{ch.title}' | "
            f"팩트: {ch.required_facts} | 핵심포인트 {len(ch.key_points)}개"
        )

    logger.info(f"🤖 [차별화] {len(diffs)}개")
    for d in diffs:
        logger.info(f"🤖   [{d.type}] {d.title}: {d.description[:60]}...")

    logger.info(f"🤖 [작성 지침] 톤: {wi.tone} | 수준: {wi.reading_level}")
    logger.info(f"🤖   반드시 포함: {wi.must_include}")
    logger.info(f"🤖   반드시 피하기: {wi.must_avoid}")
    logger.info("🤖 ===================================================================")

    return {
        "insight_pack": final_pack.model_dump()
    }


# =============================================================================
# Helper Functions
# =============================================================================

def _generate_draft(context_str: str) -> InsightPack:
    """Pass 1: 창의적인 초안 생성 (Temperature 높게)"""
    llm = ChatAnthropic(model=MODEL_NAME, temperature=0.7)
    structured_llm = llm.with_structured_output(InsightPack)

    system_prompt = """You are a visionary 'Content Strategist' for YouTube.
Your goal is to find a 'Blue Ocean' strategy in a crowded market.

**LANGUAGE RULE**:
- All output fields (Thesis, Positioning, Chapter Titles, Goals, Key Points, Hook Plan) MUST be written in Korean.
- Even if the research data contains English, the output must be natural Korean.

**CORE PHILOSOPHY**:
- **Differentiation is Key**: If the competitors said it, we usually shouldn't repeat it unless we add a new twist.
- **Hook First**: Design a hook that stops the scroll immediately.
- **Evidence-Based**: Build arguments on the provided Fact IDs.
- **MANDATORY FACT ASSIGNMENT**: Each chapter MUST have 2-3 specific Fact IDs in its 'required_facts' list.

**TASK**:
Draft a Content Blueprint (InsightPack) based on the research provided.
Focus on finding a unique 'Thesis' that contradicts or expands on the competitors.

**CRITICAL REQUIREMENTS**:
1. **Hook Plan**:
   - hook_scripts MUST include 'uses_fact_ids' with at least 1 Fact ID
   - Choose the most compelling/shocking facts for the hook
   - **MANDATORY: thumbnail_angle** - MUST include concept, copy_candidates (list), avoid (list)

2. **Story Structure - Chapters**:
   - Each chapter should have 'required_facts' with 1-3 specific Fact IDs (when available)
   - Prioritize quality over quantity - only assign facts that truly support the chapter
   - These facts should directly support the chapter's key_points

3. **Fact Selection Strategy**:
   - Prioritize Statistic and Key Event type facts
   - Ensure facts are distributed across chapters (don't use all facts in one chapter)
   - Leave some facts unused if they don't fit the narrative

4. **MANDATORY FIELDS - DO NOT SKIP**:
   - hook_plan.thumbnail_angle: MUST include {concept, copy_candidates, avoid}
   - writer_instructions: MUST include {tone, reading_level, must_include, must_avoid, claim_policy}
"""
    user_prompt = f"""
[RESEARCH DATA]
{context_str}

**INSTRUCTION**:
Generate the Draft Insight Pack. Risk-taking is encouraged regarding the angle/hook.

**REMINDER**:
- Assign 'required_facts' (1-3 Fact IDs per chapter) based on what's available. Quality over quantity!
- DO NOT forget thumbnail_angle and writer_instructions - these are REQUIRED!
"""
    return structured_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])


def _critique_and_refine(context_str: str, draft: InsightPack) -> InsightPack:
    """Pass 2: 비평 및 수정 (Temperature 낮게)"""
    llm = ChatAnthropic(model=MODEL_NAME, temperature=0.2)
    structured_llm = llm.with_structured_output(InsightPack)

    draft_json = draft.model_dump_json(indent=2)

    system_prompt = """You are a strict 'Content Editor'.
Your job is to review the Strategist's Draft and fix any logical flaws, clichés, or hallucinations.

**LANGUAGE RULE**:
- Ensure all final fields are in Korean.
- If the Draft contains English titles or descriptions, translate them into natural, compelling Korean.

**CHECKLIST**:
1. **Cliché Check**: Check the 'Common Gaps' in the research. Does the Draft's thesis actually address them? If it repeats competitors, REWRITE it.
2. **Fact Check**: Verify 'fact_ids' and 'required_facts'. Do NOT invent IDs. If a claim lacks a fact ID, remove it or mark it as an opinion.
3. **REQUIRED_FACTS VALIDATION**:
   - Each chapter should have 1-3 Fact IDs in 'required_facts' (when available)
   - If a chapter has empty required_facts, ADD appropriate Fact IDs from the available facts
   - Ensure the selected facts actually support the chapter's content
   - Quality over quantity - don't force facts that don't fit
4. **Tone Check**: Does the hook and writing instruction match the Channel Profile?

**ACTION**:
Return the REFINED InsightPack. If the Draft is good, keep it. If flawed, fix it.
"""
    user_prompt = f"""
[RESEARCH DATA]
{context_str}

[DRAFT STRATEGY]
{draft_json}

**INSTRUCTION**:
Critique and Refine this draft. Output the Final Insight Pack.
"""
    return structured_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])


def _calculate_fact_priority(fact: Dict) -> int:
    score = 0
    category = fact.get("category", "")
    if category == "Statistic":
        score += 10
    elif category == "Event":
        score += 10
    elif category == "Quote":
        score += 7
    else:
        score += 5
    if fact.get("value") and fact.get("value") != "N/A":
        score += 3
    if fact.get("visual_proposal") and fact.get("visual_proposal") != "None":
        score += 2
    return score


def _parse_competitor_data(raw_data: Dict) -> Optional[CompetitorAnalysisResult]:
    if not raw_data:
        return None
    try:
        return CompetitorAnalysisResult(**raw_data)
    except Exception as e:
        logger.warning(f"🤖 Competitor Data Schema Mismatch: {e}")
        return None


def _build_context_string(topic: str, channel: Dict, facts: List[Dict], competitor: Optional[CompetitorAnalysisResult]) -> str:
    t_str = f"""
## TOPIC (Main Subject)
**Video Topic**: {topic}
**IMPORTANT**: All strategy and content MUST be specifically about this topic.
"""

    c_str = f"""
## A. CHANNEL PROFILE
- Name: {channel.get('name', 'Unknown')}
- Category: {channel.get('category', 'General')}
- Target: {channel.get('target_audience', 'General Public')}
- Tone: {channel.get('tone', 'Informative')}
"""
    if channel.get("one_liner"):
        c_str += f"- Identity: {channel['one_liner']}\n"
    if channel.get("persona_summary"):
        c_str += f"- Channel Summary: {channel['persona_summary']}\n"
    if channel.get("content_style"):
        c_str += f"- Content Style: {channel['content_style']}\n"
    if channel.get("differentiator"):
        c_str += f"- Differentiator: {channel['differentiator']}\n"
    if channel.get("audience_needs"):
        c_str += f"- Audience Needs: {channel['audience_needs']}\n"
    if channel.get("main_topics"):
        c_str += f"- Main Topics: {', '.join(channel['main_topics'])}\n"

    f_str = "\n## B. FACT PACK (Available Evidence)\n"
    if facts:
        valid_facts = [f for f in facts if f.get("id")]
        if len(valid_facts) < len(facts):
            dropped_count = len(facts) - len(valid_facts)
            logger.warning(f"🤖 Dropped {dropped_count} facts without IDs")

        source_best: Dict[Any, Dict] = {}
        for f in valid_facts:
            src_idx = f.get("source_index", -1)
            if src_idx not in source_best or _calculate_fact_priority(f) > _calculate_fact_priority(source_best[src_idx]):
                source_best[src_idx] = f

        guaranteed = list(source_best.values())
        guaranteed_ids = {f["id"] for f in guaranteed}

        remaining = [f for f in valid_facts if f["id"] not in guaranteed_ids]
        remaining_sorted = sorted(remaining, key=_calculate_fact_priority, reverse=True)

        prioritized_facts = guaranteed + remaining_sorted
        prioritized_facts = prioritized_facts[:15]

        for f in prioritized_facts:
            f_id = f["id"]
            content = f.get("content", "")[:300]
            val = f.get("value", "N/A")
            f_str += f"- [ID: {f_id}] {content} (Value: {val})\n"
    else:
        f_str += "(No specific facts found.)\n"

    comp_str = "\n## C. COMPETITOR ANALYSIS\n"
    if competitor:
        ci = competitor.cross_insights
        if ci:
            comp_str += f"1. Common Gaps (Must Address): {', '.join(ci.common_gaps[:5])}\n"
            comp_str += f"2. Formatting Do's/Don'ts: {', '.join(ci.do_and_dont[:3])}\n"
        comp_str += "3. Competitor Videos:\n"
        for v in competitor.video_analyses[:3]:
            # 새 스키마: strengths/weaknesses, 이전 스키마: hook_analysis/weak_points 호환
            strengths = v.strengths if hasattr(v, 'strengths') else []
            weaknesses = v.weaknesses if hasattr(v, 'weaknesses') else []
            strength_short = ', '.join(strengths[:2]) if strengths else 'N/A'
            weakness_short = ', '.join(weaknesses[:2]) if weaknesses else 'N/A'
            comp_str += f"   - [{v.title[:50]}] Strengths: {strength_short} | Weakness: {weakness_short}\n"
    else:
        comp_str += "(Competitor analysis not available or schema mismatch)\n"

    return t_str + c_str + f_str + comp_str
