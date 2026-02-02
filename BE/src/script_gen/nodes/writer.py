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
from datetime import datetime
from typing import Dict, Any, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from src.script_gen.schemas.writer import Script, ScriptDraft, QualityReport

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

MODEL_NAME = "gpt-4o-mini"


def writer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Writer Node: Insight Blueprint를 바탕으로 대본 작성
    
    Input (from state):
        - insight_pack: Insight Builder의 결과
        - news_data: News Research의 결과 (facts)
    
    Output (to state):
        - script_draft: ScriptDraft 객체
    """
    logger.info("Writer Node 시작")
    
    # 1. 입력 데이터 추출
    insight_pack = state.get("insight_pack", {})
    news_data = state.get("news_data", {})
    facts = news_data.get("structured_facts", [])
    channel_profile = state.get("channel_profile", {})
    
    # 2. Context 조립
    context_str = _build_writer_context(channel_profile, insight_pack, facts)
    
    # 3. Draft 생성 (LLM 호출)
    draft_script = _generate_draft_script(context_str, insight_pack)
    
    # 4. Quality Report 생성
    quality_report = _build_quality_report(draft_script, insight_pack, facts)
    
    # 5. ScriptDraft 객체 생성
    script_draft = ScriptDraft(
        script_draft_id=f"scd_{uuid.uuid4().hex[:8]}",
        topic_request_id=state.get("topic_request_id"),
        generated_at=datetime.utcnow().isoformat(),
        metadata={
            "title": insight_pack.get("positioning", {}).get("thesis", "Untitled"),
            "hookType": insight_pack.get("hook_plan", {}).get("hook_type", "curiosity"),
            "estimatedDurationMin": 10,
            "readingLevel": insight_pack.get("writer_instructions", {}).get("reading_level", "intermediate")
        },
        script=draft_script,
        claims=[],  # Phase 2에서 구현
        source_map=[],  # Phase 2에서 구현
        quality_report=quality_report
    )
    
    logger.info(f"Writer 완료: {len(draft_script.chapters)}개 챕터 생성")
    logger.info(f"Fact 사용률: {len(quality_report.used_fact_ids)}개 사용")
    
    return {
        "script_draft": script_draft.model_dump()
    }


# =============================================================================
# Helper Functions
# =============================================================================

def _generate_draft_script(context_str: str, insight_pack: Dict) -> Script:
    """Phase 1: Draft 생성 (Structured Output 사용)"""
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0.6)
    structured_llm = llm.with_structured_output(Script)
    
    system_prompt = """You are an expert YouTube scriptwriter specializing in evidence-based content.
Your goal is to write an engaging script that STRICTLY follows the provided Insight Blueprint and CITES FACTS.

**CRITICAL RULES**:
1. **Follow the Blueprint**: Use the exact chapter structure and hook strategy from the Insight Blueprint.
2. **FACT CITATION (Flexible)**: 
   - MAJOR claims, statistics, or key statements MUST reference a Fact ID from the available facts
   - Minor transitions, opinions, or general statements don't need citations
   - Aim for at least 1-2 Fact IDs per chapter (use more if available)
   - Example: "According to recent data (fact-abc123), AI chip demand surged by 40%"
3. **Conversational Tone**: Write like you're talking to a friend, not reading a textbook.
4. **Hook First**: The first 15 seconds must grab attention immediately using facts from the hook plan.
5. **Visual Cues**: Suggest on-screen elements (charts, images) where helpful.

**FACT USAGE POLICY**:
- Use ONLY the Fact IDs provided in the context
- DO NOT make up statistics or claims without a corresponding Fact ID
- If facts are limited, focus them on the most important claims
- It's okay to have narrative flow without constant citations

**OUTPUT**: Generate a Script object with hook, chapters (citing facts where important), and closing.
"""

    user_prompt = f"""
{context_str}

**TASK**:
Write the full YouTube script following the Insight Blueprint.

**REQUIREMENTS**:
1. **Hook**: 
   - Use the hook strategy provided
   - Include at least 1 Fact ID from the hook plan's uses_fact_ids
   - **IMPORTANT**: Fill the `fact_references` field with the Fact IDs you cite in the hook text
   
2. **Chapters**: 
   - Follow the chapter structure exactly
   - Each chapter should use 1-2 facts from its "required_facts" (when available)
   - **IMPORTANT**: For each Beat, fill the `fact_references` field with the Fact IDs you cite in that beat's narration
   
3. **Fact Citation Format**:
   - In narration: "Studies show (fact-xyz789) that..." or "According to recent data (fact-abc123)..."
   - In fact_references: ["fact-xyz789"] or ["fact-abc123", "fact-def456"]
   - The fact_references field should list ALL Fact IDs mentioned in that beat
   
4. **Closing**: 
   - End with the CTA from the blueprint
   - Optionally reference a final compelling fact

**EXAMPLE BEAT OUTPUT**:
```json
{{
  "beat_id": "b1",
  "purpose": "evidence",
  "line": "So why is this happening? Well, according to recent market analysis (fact-a1b2c3), NVIDIA's GPU shipments increased by 45% in Q4 2024. This isn't just a coincidence - industry experts (fact-d4e5f6) predict this trend will continue through 2025.",
  "fact_references": ["fact-a1b2c3", "fact-d4e5f6"],
  "claims": [],
  "on_screen_cues": [],
  "broll_ideas": []
}}
```

Generate the Script now. Remember: Fill `fact_references` for every Beat and Hook!
"""
    
    return structured_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])


def _build_writer_context(channel: Dict, insight: Dict, facts: List[Dict]) -> str:
    """LLM 입력용 컨텍스트 조립"""
    
    # 1. Channel Profile
    c_str = f"""
## CHANNEL PROFILE
- Name: {channel.get('name', 'Unknown')}
- Target Audience: {channel.get('target_audience', 'General')}
- Tone: {channel.get('tone', 'Informative')}
"""

    # 2. Insight Blueprint (간략하게)
    positioning = insight.get("positioning", {})
    hook_plan = insight.get("hook_plan", {})
    story_structure = insight.get("story_structure", {})
    
    i_str = f"""
## INSIGHT BLUEPRINT

**Positioning**:
- Thesis: {positioning.get('thesis', 'N/A')}
- Promise: {positioning.get('one_sentence_promise', 'N/A')}

**Hook Strategy** ({hook_plan.get('hook_type', 'curiosity')}):
"""
    for h in hook_plan.get("hook_scripts", []):
        i_str += f"- {h.get('text', '')}\n"
    
    i_str += "\n**Chapter Structure**:\n"
    for ch in story_structure.get("chapters", []):
        i_str += f"- {ch.get('title', 'Chapter')}: {ch.get('goal', '')}\n"
        i_str += f"  Key Points: {', '.join(ch.get('key_points', []))}\n"
        i_str += f"  Required Facts: {', '.join(ch.get('required_facts', []))}\n"
    
    # 3. Available Facts (상위 15개)
    f_str = "\n## AVAILABLE FACTS (Use these for evidence)\n"
    for f in facts[:15]:
        f_id = f.get("id", "unknown")
        content = f.get("content", "")[:150]
        category = f.get("category", "")
        f_str += f"- [{f_id}] ({category}) {content}\n"
    
    return c_str + i_str + f_str


def _build_quality_report(script: Script, insight_pack: Dict, facts: List[Dict]) -> QualityReport:
    """
    Quality Report 생성: fact_references에서 사용된 Fact ID 추출
    """
    used_fact_ids = set()
    
    # 1. Hook에서 Fact ID 추출
    if hasattr(script.hook, 'fact_references'):
        used_fact_ids.update(script.hook.fact_references)
    
    # 2. 각 Chapter의 Beat에서 Fact ID 추출
    for chapter in script.chapters:
        for beat in chapter.beats:
            if hasattr(beat, 'fact_references'):
                used_fact_ids.update(beat.fact_references)
    
    # 3. Required Facts 확인
    required_fact_ids = set()
    story_structure = insight_pack.get("story_structure", {})
    for ch in story_structure.get("chapters", []):
        required_fact_ids.update(ch.get("required_facts", []))
    
    unused_required = list(required_fact_ids - used_fact_ids)
    
    logger.info(f"Quality Report: {len(used_fact_ids)}개 Fact 사용, {len(unused_required)}개 필수 Fact 미사용")
    
    return QualityReport(
        used_fact_ids=list(used_fact_ids),
        unused_required_fact_ids=unused_required,
        policy_checks={"noUnsourcedNumbers": len(used_fact_ids) > 0}
    )
