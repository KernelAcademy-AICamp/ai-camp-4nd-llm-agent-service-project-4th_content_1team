"""
Intent Analyzer Node - 독자 의도 분석 에이전트
Planner 실행 전, 주제의 시청자 의도(Reader Intent)를 먼저 파악합니다.
이를 통해 Planner가 시청자가 진짜 원하는 것을 기반으로 기획안을 생성하게 합니다.
"""
from typing import Dict, Any
from langchain_openai import ChatOpenAI
import json
import logging
import re

logger = logging.getLogger(__name__)

OPENAI_MODEL = "gpt-4o"

SYSTEM_PROMPT = """당신은 콘텐츠 전략가입니다.
주어진 유튜브 주제에 대해 시청자의 실제 의도를 분석하고,
콘텐츠가 다뤄야 할 핵심 질문과 하위 주제를 구조화된 JSON으로 반환합니다.

반드시 다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{
  "core_question": "시청자가 이 주제를 검색할 때 가장 원하는 핵심 질문",
  "reader_pain_point": "시청자가 현재 겪고 있는 고민이나 불편함",
  "reader_desire": "시청자가 이 콘텐츠를 보고 얻고 싶은 결과",
  "intent_mix": {
    "informational": 40,
    "emotional": 30,
    "actionable": 30
  },
  "content_angle": "콘텐츠가 취해야 할 접근 각도 (예: 비교형, 해결형, 폭로형 등)",
  "sub_topics": [
    {
      "topic": "다뤄야 할 하위 주제",
      "reason": "이 주제를 다뤄야 하는 이유",
      "search_hint": "관련 검색 키워드 힌트"
    }
  ]
}

주의사항:
- intent_mix의 세 값의 합은 반드시 100이어야 합니다
- sub_topics는 3~5개를 반환하세요
- 모든 텍스트는 한국어로 작성하세요"""


async def intent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    주제를 받아 시청자 의도를 분석하는 노드.
    Planner 이전에 실행되어 content_angle, sub_topics 등을 제공합니다.

    Args:
        state: ScriptGenState (topic 포함)

    Returns:
        {"intent_analysis": {...}} — 실패 시 {"intent_analysis": {}}
    """
    topic = state.get("topic", "")
    if not topic:
        logger.warning("[IntentAnalyzer] topic이 없어 분석을 건너뜁니다.")
        return {"intent_analysis": {}}

    logger.info(f'[IntentAnalyzer] 주제: "{topic}"')

    user_prompt = f'주제: "{topic}" → 위 형식의 JSON을 반환하세요.'

    try:
        llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0.3)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        response = await llm.ainvoke(messages)
        result = _parse_json(response.content)
        _log_result(topic, result)
        return {"intent_analysis": result}

    except Exception as e:
        logger.warning(f"[IntentAnalyzer] 분석 실패 (파이프라인 계속 진행): {e}")
        return {"intent_analysis": {}}


# ---------------------------------------------------------------------------
# 헬퍼 함수
# ---------------------------------------------------------------------------

def _parse_json(text: str) -> Dict[str, Any]:
    """LLM 응답 텍스트에서 JSON 객체를 추출합니다."""
    # 코드 블록 제거
    code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if code_block:
        return json.loads(code_block.group(1))

    # 중괄호 균형으로 JSON 객체 추출
    start = text.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(text[start : i + 1])

    # 전체 텍스트 파싱 시도
    return json.loads(text.strip())


def _log_result(topic: str, result: Dict[str, Any]) -> None:
    """분석 결과를 구조화된 형식으로 로깅합니다."""
    intent_mix = result.get("intent_mix", {})
    sub_topics = result.get("sub_topics", [])

    lines = [
        "[IntentAnalyzer] 결과:",
        f"  core_question    : {result.get('core_question', '-')}",
        f"  reader_pain_point: {result.get('reader_pain_point', '-')}",
        f"  reader_desire    : {result.get('reader_desire', '-')}",
        f"  intent_mix       : informational={intent_mix.get('informational', 0)} / "
        f"emotional={intent_mix.get('emotional', 0)} / actionable={intent_mix.get('actionable', 0)}",
        f"  content_angle    : {result.get('content_angle', '-')}",
        "  sub_topics       :",
    ]
    for idx, st in enumerate(sub_topics, 1):
        lines.append(
            f"    {idx}. [{st.get('topic', '')}] — {st.get('reason', '')} (hint: {st.get('search_hint', '')})"
        )
    logger.info("\n".join(lines))
