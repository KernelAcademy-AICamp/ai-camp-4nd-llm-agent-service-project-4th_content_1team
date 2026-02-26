"""
Planner Node - 콘텐츠 기획 에이전트

Intent Analyzer 결과를 받아:
  1. content_angle — intent_analyzer가 제시한 앵글을 reader 심리 기반으로 디벨롭
  2. research_plan  — sub_topics search_hint를 기반으로 리서치 키워드 + 활용법 구성
                      (필요 시 디벨롭된 앵글에 맞춰 키워드 추가)
                      youtube_keywords: 유사 유튜브 영상 검색용 2개

Downstream 호환 필드:
  - researchPlan.newsQuery → news_research_node
  - search_queries         → yt_fetcher_node
"""
from typing import Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
import json
import logging
import re
import asyncio

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
OPENAI_MODEL = "gpt-4o"


class ValidationError(Exception):
    """Planner 출력 검증 실패"""
    pass


# =============================================================================
# 메인 노드 함수
# =============================================================================

async def planner_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Intent Analyzer 결과를 이어받아 콘텐츠 앵글(1개)과 리서치 플랜을 생성합니다.

    Args:
        state: ScriptGenState (topic, channel_profile, intent_analysis 포함)

    Returns:
        {"content_brief": {"content_angle": {...}, "research_plan": {...}}}
    """
    topic = state.get("topic")
    channel_profile = state.get("channel_profile", {})
    intent_analysis = state.get("intent_analysis") or {}

    if not topic:
        raise ValueError("Topic is required in state")

    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"[Planner] 시도 {attempt + 1}/{MAX_RETRIES}")

            prompt = _build_planner_prompt(
                topic=topic,
                channel_profile=channel_profile,
                intent_analysis=intent_analysis,
                attempt=attempt,
                last_error=last_error,
            )

            llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0.4)
            response = await llm.ainvoke(prompt)

            content_brief = _parse_llm_response(response.content)
            _validate_content_brief(content_brief)

            # downstream 노드용 호환 필드 추가
            _derive_downstream_fields(content_brief, state)

            logger.info("✅ [Planner] 성공: 앵글 디벨롭 + 리서치 플랜 생성 완료")
            _log_result(topic, content_brief)
            return {"content_brief": content_brief}

        except ValidationError as e:
            last_error = str(e)
            logger.warning(f"⚠️ [Planner] 시도 {attempt + 1} 실패: {e}")
            if attempt == MAX_RETRIES - 1:
                raise RuntimeError(
                    f"콘텐츠 기획안 생성에 실패했습니다. 잠시 후 다시 시도해주세요. (오류: {e})"
                )
            wait_time = 2 ** attempt
            logger.info(f"[Planner] {wait_time}초 후 재시도...")
            await asyncio.sleep(wait_time)

        except json.JSONDecodeError as e:
            last_error = f"JSON parse error: {str(e)}"
            logger.warning(f"⚠️ [Planner] JSON 파싱 실패: {e}")
            if attempt == MAX_RETRIES - 1:
                raise RuntimeError("LLM이 올바른 형식으로 응답하지 않았습니다. 잠시 후 다시 시도해주세요.")
            await asyncio.sleep(2 ** attempt)

    raise RuntimeError("Unexpected error in planner_node")


# =============================================================================
# 헬퍼: downstream 호환 필드 추출
# =============================================================================

def _derive_downstream_fields(content_brief: Dict, state: Dict) -> None:
    """
    새 구조에서 downstream 노드가 필요로 하는 필드를 추출합니다.

    - researchPlan.newsQuery  → news_research_node
    - search_queries          → yt_fetcher_node
    """
    research_plan = content_brief.get("research_plan", {})

    # ── news_research_node ──
    sources = research_plan.get("sources", [])
    news_keywords = [s["keyword"] for s in sources if s.get("keyword")]
    content_brief["researchPlan"] = {
        "newsQuery": news_keywords,
        "freshnessDays": 30,
    }

    # ── yt_fetcher_node ──
    content_brief["search_queries"] = research_plan.get("youtube_keywords", [])


# =============================================================================
# 헬퍼: 프롬프트 생성
# =============================================================================

def _build_planner_prompt(
    topic: str,
    channel_profile: Dict,
    intent_analysis: Dict,
    attempt: int = 0,
    last_error: Optional[str] = None,
) -> str:
    """
    Planner 프롬프트 생성.

    구성:
        1. Role & Task
        2. Intent Analyzer 결과 (핵심 입력)
        3. 채널 페르소나 (보조 입력)
        4. 출력 형식 지시
    """

    # ── Intent Analyzer 결과 ──────────────────────────────────────────────────
    # 이 블록이 Planner의 핵심 입력
    intent_block = ""
    sub_topics_hint = []
    if intent_analysis:
        intent_mix = intent_analysis.get("intent_mix", {})
        sub_topics = intent_analysis.get("sub_topics", [])
        base_angle = intent_analysis.get("content_angle", "")

        intent_block = "\n\n## 📊 Intent Analyzer 결과 (핵심 입력)\n"
        intent_block += f"- 기본 컨텐츠 앵글: **{base_angle}** ← 이것을 디벨롭할 것\n"
        intent_block += f"- 핵심 질문: {intent_analysis.get('core_question', '')}\n"
        intent_block += f"- 시청자 고민: {intent_analysis.get('reader_pain_point', '')}\n"
        intent_block += f"- 시청자 욕구: {intent_analysis.get('reader_desire', '')}\n"
        intent_block += (
            f"- 의도 비율: 정보형 {intent_mix.get('informational', 0)}% / "
            f"감성형 {intent_mix.get('emotional', 0)}% / "
            f"실행형 {intent_mix.get('actionable', 0)}%\n"
        )
        if sub_topics:
            intent_block += "- 하위 주제 및 리서치 키워드 (research_plan 시작점):\n"
            for st in sub_topics:
                hint = st.get("search_hint", "")
                intent_block += (
                    f"  • [{st.get('topic', '')}] {st.get('reason', '')} "
                    f"→ 검색힌트: \"{hint}\"\n"
                )
                if hint:
                    sub_topics_hint.append(hint)

    # ── 채널 페르소나 (보조) ──────────────────────────────────────────────────
    persona_block = "\n\n## 🎙️ 채널 페르소나 (참고)\n"
    persona_block += f"- 채널명: {channel_profile.get('name', 'Unknown')}\n"
    persona_block += f"- 타겟 시청자: {channel_profile.get('target_audience', '일반 시청자')}\n"
    if channel_profile.get("content_style"):
        persona_block += f"- 콘텐츠 스타일: {channel_profile['content_style']}\n"
    if channel_profile.get("differentiator"):
        persona_block += f"- 차별점: {channel_profile['differentiator']}\n"

    # ── 출력 형식 ─────────────────────────────────────────────────────────────
    hint_example = sub_topics_hint[0] if sub_topics_hint else "AI 코딩 도구 생산성 연구"
    format_instruction = f"""

## 📋 출력 형식 (이 JSON만 반환)

```json
{{
  "content_angle": {{
    "angle": "기본 앵글을 reader 심리 기반으로 구체화한 최종 앵글",
    "description": "이 앵글로 접근하는 이유 — 시청자 고민과 욕구에 어떻게 응답하는지 설명",
    "hook": "이 앵글로 시청자를 사로잡을 첫 마디 (훅 문장)"
  }},
  "research_plan": {{
    "sources": [
      {{
        "keyword": "{hint_example}",
        "how_to_use": "영상의 어느 부분에서, 어떤 방식으로 활용할지"
      }}
    ],
    "youtube_keywords": [
      "비슷한 주제 유튜브 검색 키워드 1",
      "비슷한 주제 유튜브 검색 키워드 2"
    ]
  }}
}}
```

## ✅ 작성 규칙

**content_angle:**
- `angle`: Intent Analyzer의 content_angle을 그대로 쓰지 말고, core_question + reader_pain_point + reader_desire를 모두 반영하여 더 구체적으로 디벨롭
- `description`: "왜 이 앵글인가?" — 시청자 고민과 욕구에 어떻게 응답하는지 명확히
- `hook`: 시청자가 영상을 클릭하게 만들 첫 마디 (질문형 또는 도발형)

**research_plan.sources:**
- Intent Analyzer의 하위 주제 검색힌트를 **반드시 포함** (시작점)
- 디벨롭된 앵글에 맞게 **추가 키워드 보완 가능**
- 각 소스의 `how_to_use`: 영상에서 **어느 섹션에서 어떤 방식으로** 쓸지 구체적으로
- 최소 3개, 권장 5~7개
- ⚠️ `keyword`는 **단일 검색어**만 사용 — 쉼표(,) 절대 금지, 짧고 명확하게 (예: "Claude Code 활용법", "AI 코딩 도구 비교")

**research_plan.youtube_keywords:**
- 정확히 2개
- 비슷한 주제의 다른 유튜브 영상을 찾기 위한 한국어 검색어

**공통:**
- 모든 텍스트는 한국어
- 순수 JSON만 반환 (설명 없이)
"""

    base_prompt = f"""당신은 유튜브 콘텐츠 전략가입니다.
Intent Analyzer가 분석한 결과를 받아, 시청자 심리에 최적화된 콘텐츠 앵글과 리서치 플랜을 생성합니다.

## 🎯 주제
{topic}
{intent_block}{persona_block}

## 📌 작업 지시

**STEP 1: content_angle 디벨롭**
- Intent Analyzer의 `content_angle`(기본 앵글)을 출발점으로 삼아
- `core_question`이 궁금증을 유발하도록, `reader_pain_point`가 해소되도록, `reader_desire`가 충족되도록
- 세 요소를 통합하여 더 구체적이고 설득력 있는 앵글로 발전시키세요
- 의도 비율(정보/감성/실행)에 맞게 앵글의 tone을 조정하세요

**STEP 2: research_plan 작성**
- 하위 주제 검색힌트를 먼저 sources에 포함 (각각 how_to_use 작성)
- 디벨롭된 앵글을 더 잘 뒷받침하기 위해 필요한 키워드 추가
- youtube_keywords: 이 주제와 비슷한 영상을 찾을 수 있는 검색어 2개
{format_instruction}

주제 "{topic}"에 대한 기획안을 JSON으로만 반환하세요:"""

    # ── 재시도 피드백 ─────────────────────────────────────────────────────────
    if attempt > 0 and last_error:
        return f"""[재시도 {attempt + 1}회차]
이전 응답 오류: {last_error}

수정 필수:
- content_angle: angle / description / hook 모두 비어있으면 안 됨
- research_plan.sources: 최소 3개, 각각 keyword + how_to_use 포함
- research_plan.youtube_keywords: 정확히 2개

{base_prompt}"""

    return base_prompt


# =============================================================================
# 헬퍼: JSON 파싱
# =============================================================================

def _parse_llm_response(response_text: str) -> Dict:
    """LLM 응답에서 JSON 객체를 추출합니다."""

    # 전략 1: 코드 블록 (```json ... ```)
    code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
    if code_block:
        try:
            return json.loads(code_block.group(1))
        except json.JSONDecodeError:
            pass

    # 전략 2: 중괄호 균형 탐색
    start_idx = response_text.find("{")
    if start_idx != -1:
        depth = 0
        for i in range(start_idx, len(response_text)):
            if response_text[i] == "{":
                depth += 1
            elif response_text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(response_text[start_idx : i + 1])
                    except json.JSONDecodeError:
                        break

    # 전략 3: 전체 텍스트
    try:
        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        logger.error(f"[Planner] JSON 파싱 실패: {response_text[:200]}...")
        raise json.JSONDecodeError("Could not extract valid JSON", response_text, 0)


# =============================================================================
# 헬퍼: 검증
# =============================================================================

def _validate_content_brief(brief: Dict) -> None:
    """
    Planner 출력 유효성 검증.
    실패 시 ValidationError 발생.
    """
    # 필수 최상위 필드
    for field in ["content_angle", "research_plan"]:
        if field not in brief:
            raise ValidationError(f"필수 필드 없음: {field}")

    # content_angle: 단일 객체
    angle = brief.get("content_angle", {})
    if not isinstance(angle, dict):
        raise ValidationError("content_angle은 객체여야 합니다")
    for sub in ["angle", "description", "hook"]:
        if not angle.get(sub, "").strip():
            raise ValidationError(f"content_angle.{sub} 가 비어있습니다")

    # research_plan 구조
    rp = brief.get("research_plan", {})
    if not isinstance(rp, dict):
        raise ValidationError("research_plan은 객체여야 합니다")

    # sources: 최소 3개, 각 항목에 keyword + how_to_use
    sources = rp.get("sources", [])
    if not isinstance(sources, list) or len(sources) < 3:
        raise ValidationError(
            f"research_plan.sources는 최소 3개여야 합니다 (현재: {len(sources)}개)"
        )
    for i, src in enumerate(sources, 1):
        for sub in ["keyword", "how_to_use"]:
            if not src.get(sub, "").strip():
                raise ValidationError(
                    f"research_plan.sources[{i}].{sub} 가 비어있습니다"
                )

    # youtube_keywords: 정확히 2개
    yt_kw = rp.get("youtube_keywords", [])
    if not isinstance(yt_kw, list) or len(yt_kw) != 2:
        raise ValidationError(
            f"research_plan.youtube_keywords는 정확히 2개여야 합니다 (현재: {len(yt_kw)}개)"
        )
    for kw in yt_kw:
        if not str(kw).strip():
            raise ValidationError("research_plan.youtube_keywords에 빈 항목이 있습니다")


# =============================================================================
# 헬퍼: 로깅
# =============================================================================

def _log_result(topic: str, brief: Dict) -> None:
    """Planner 결과를 구조화된 형식으로 로깅합니다."""
    angle = brief.get("content_angle", {})
    sources = brief.get("research_plan", {}).get("sources", [])
    yt_kw = brief.get("research_plan", {}).get("youtube_keywords", [])

    lines = [
        f"[Planner] 결과 — {topic!r}",
        f"  앵글: [{angle.get('angle', '')}]",
        f"  설명: {angle.get('description', '')}",
        f"  훅:   {angle.get('hook', '')}",
        f"  리서치 소스 ({len(sources)}개):",
    ]
    for s in sources:
        lines.append(f"    • \"{s.get('keyword', '')}\" → {s.get('how_to_use', '')}")
    lines.append(f"  유튜브 키워드: {yt_kw}")
    logger.info("\n".join(lines))
