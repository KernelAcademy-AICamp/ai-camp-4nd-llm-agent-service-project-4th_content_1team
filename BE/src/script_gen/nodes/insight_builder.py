"""
Insight Builder Node - 콘텐츠 전략 설계자 (2-Pass Architecture)
"내 영상만의 차별화 포인트(Insight)"를 도출하고, Writer가 대본을 쓸 수 있도록 구체적인 설계도(Blueprint)를 생성합니다.

Architecture (2-Pass):
    1. Pass 1 (Draft): 창의적인 전략과 차별화 포인트 도출 (Creative Mode)
    2. Pass 2 (Critic): 경쟁사 중복 체크, 팩트 검증, 톤 보정 (Strict Mode)
"""

import logging
import uuid
import json
from typing import Dict, Any, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate

from src.script_gen.schemas.insight import InsightPack
from src.script_gen.schemas.competitor import CompetitorAnalysisResult

# .env 로드
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# 모델 설정 (Pass 1은 창의성, Pass 2는 논리성)
MODEL_NAME = "gpt-4o"

def insight_builder_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Insight Builder Node (2-Pass) 시작")
    
    # Fan-in Guard: competitor_data가 아직 없으면 skip (GPT 호출 낭비 방지)
    if state.get("competitor_data") is None:
        logger.info("Insight Builder: competitor 분석 대기 중, skip")
        return {}
    
    # --- 1. 입력 데이터 파싱 및 안전한 변환 ---
    topic = state.get("topic", "Unknown Topic")  # [FIX] 주제 추가
    channel_profile = state.get("channel_profile", {})
    
    # Fact Pack (List[Dict])
    news_data = state.get("news_data", {})
    facts = news_data.get("structured_facts", []) 
    
    # Competitor Pack (Dict -> Pydantic)
    raw_comp_data = state.get("competitor_data", {})
    competitor_result = _parse_competitor_data(raw_comp_data)
    
    # Context 조립 - topic 전달
    context_str = _build_context_string(topic, channel_profile, facts, competitor_result)
    
    
    # --- 2. Pass 1: Draft Generation (Creative) with Retry ---
    logger.info("Pass 1: Creating Strategy Draft...")
    draft_pack = None
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            draft_pack = _generate_draft(context_str)
            break  # 성공하면 루프 탈출
        except Exception as e:
            logger.warning(f"Draft 생성 실패 (시도 {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise  # 마지막 시도도 실패하면 에러 발생
    
    
    # --- 3. Pass 2: Critic & Repair (Strict) with Retry ---
    logger.info("Pass 2: Critiquing and Refining...")
    final_pack = None
    
    for attempt in range(max_retries):
        try:
            final_pack = _critique_and_refine(context_str, draft_pack)
            break
        except Exception as e:
            logger.warning(f"Refine 실패 (시도 {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise
    
    
    # --- 4. Finalize ---
    # ID가 없으면 생성
    if not final_pack.insight_pack_id:
        final_pack.insight_pack_id = f"ins_{uuid.uuid4().hex[:8]}"

    logger.info(f"Insight Builder 완료: {final_pack.positioning.thesis}")
    
    return {
        "insight_pack": final_pack.model_dump()
    }


# =============================================================================
# Helper Functions (Logic)
# =============================================================================

def _generate_draft(context_str: str) -> InsightPack:
    """Pass 1: 창의적인 초안 생성 (Temperature 높게)"""
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0.7)
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
   - Example: If a chapter is about "Market Growth", required_facts should include statistics about growth
   
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
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0.2) # 논리적 검증을 위해 낮춤
    structured_llm = llm.with_structured_output(InsightPack)
    
    # Draft를 JSON 문자로 변환 (Context로 넣기 위해)
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
    """팩트 우선순위 점수 계산 (높을수록 중요)"""
    score = 0
    
    category = fact.get("category", "")
    
    # 1. 카테고리별 기본 점수
    if category == "Statistic":
        score += 10  # 숫자는 여전히 중요
    elif category == "Event":
        score += 10  # 사건도 동급 (유튜브는 스토리가 강함)
    elif category == "Quote":
        score += 7   # 인용문도 훅에 좋음
    else:
        score += 5   # 일반 Fact
    
    # 2. Value(수치) 있으면 보너스
    if fact.get("value") and fact.get("value") != "N/A":
        score += 3
    
    # 3. Visual Proposal 있으면 보너스 (영상용으로 좋음)
    if fact.get("visual_proposal") and fact.get("visual_proposal") != "None":
        score += 2
    
    return score


def _parse_competitor_data(raw_data: Dict) -> Optional[CompetitorAnalysisResult]:
    """Dict 데이터를 Pydantic 모델로 변환 (실패 시 None 처리하여 로직 방어)"""
    if not raw_data:
        return None
    try:
        return CompetitorAnalysisResult(**raw_data)
    except Exception as e:
        logger.warning(f"Competitor Data Schema Mismatch: {e}")
        # 데이터가 있지만 스키마가 안 맞을 경우, 최대한 살리거나 None 반활
        # 여기서는 안전하게 None 반환하고 Context Builder에서 처리
        return None


def _build_context_string(topic: str, channel: Dict, facts: List[Dict], competitor: Optional[CompetitorAnalysisResult]) -> str:
    """LLM 입력용 컨텍스트 조립 (Context 길이 제한 적용)"""
    
    # 0. Topic (가장 중요!)
    t_str = f"""
## TOPIC (Main Subject)
**Video Topic**: {topic}
**IMPORTANT**: All strategy and content MUST be specifically about this topic.
"""
    
    # 1. Channel
    c_str = f"""
## A. CHANNEL PROFILE
- Name: {channel.get('name', 'Unknown')}
- Category: {channel.get('category', 'General')}
- Target: {channel.get('target_audience', 'General Public')}
- Tone: {channel.get('tone', 'Informative')}
"""
    # 추가 페르소나 정보 (있을 때만)
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

    # 2. Facts (상위 15개로 제한 - Context 폭발 방지)
    f_str = "\n## B. FACT PACK (Available Evidence)\n"
    if facts:
        # [FIX] ID 없는 팩트는 먼저 제거 (MISSING_ID 폭탄 방지)
        valid_facts = [f for f in facts if f.get("id")]
        if len(valid_facts) < len(facts):
            dropped_count = len(facts) - len(valid_facts)
            logger.warning(f"Dropped {dropped_count} facts without IDs (출처 불명 팩트 제외)")
        
        # [FIX] 개선된 우선순위 점수로 정렬 (Event도 고려)
        prioritized_facts = sorted(
            valid_facts,
            key=_calculate_fact_priority,
            reverse=True
        )[:15]
        
        for f in prioritized_facts:
            f_id = f["id"]  # 이제 확실히 존재함
            content = f.get("content", "")[:300]  # 길이 제한 (문맥 보존)
            val = f.get("value", "N/A")
            f_str += f"- [ID: {f_id}] {content} (Value: {val})\n"
    else:
        f_str += "(No specific facts found.)\n"

    # 3. Competitors (Schema 기반 안전 접근)
    comp_str = "\n## C. COMPETITOR ANALYSIS\n"
    if competitor:
        # Cross Insights
        ci = competitor.cross_insights
        comp_str += f"1. Common Gaps (Must Address): {', '.join(ci.common_gaps[:5])}\n"  # 상위 5개만
        comp_str += f"2. Formatting Do's/Don'ts: {', '.join(ci.do_and_dont[:3])}\n"  # 상위 3개만
        
        # Individual Videos (Top 3만, 각 필드 길이 제한)
        comp_str += "3. Competitor Videos:\n"
        for v in competitor.video_analyses[:3]:
            hook_short = v.hook_analysis[:100]  # 100자 제한
            weak_short = ', '.join(v.weak_points[:2])  # 약점 2개만
            comp_str += f"   - [{v.title[:50]}] Hook: {hook_short} | Weakness: {weak_short}\n"
    else:
        comp_str += "(Competitor analysis not available or schema mismatch)\n"
        
    return t_str + c_str + f_str + comp_str
