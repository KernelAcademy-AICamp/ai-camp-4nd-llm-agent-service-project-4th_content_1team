"""
검색 키워드 추출 에이전트.

추천 주제 제목을 기반으로 고품질 한국어 검색 키워드 3개를 생성합니다.
YouTube, 뉴스, 커뮤니티 등 크로스 플랫폼 검색에 최적화된 키워드를 생성합니다.
"""
import json
import logging
import re
from typing import List, Optional

from app.services.gemini_client import call_gemini

logger = logging.getLogger(__name__)


def _build_keyword_prompt(topic: str) -> str:
    """검색 키워드 추출 프롬프트 생성."""
    return f"""You are a cross-domain search keyword generation agent.

Your job is to convert any given content topic into exactly 3 high-quality Korean search keywords for content discovery.

These keywords will be used to collect:
- YouTube videos
- News articles
- Community / forum discussions

Your output must be optimized for cross-platform search discoverability.

--------------------------------------------------

[INPUT TOPIC]
The topic/title to convert into search keywords will be provided below:
{topic}

--------------------------------------------------

[CORE RULE]

Generate exactly 3 Korean search keywords.

Each keyword must represent one universal search intent:

1) Core Understanding Intent
2) Practical Use Intent
3) Trend / Evaluation Intent

--------------------------------------------------

[STYLE RULES]

- Korean only
- 2–5 words per keyword
- Natural search phrase
- No punctuation
- No symbols
- No version numbers
- No brand names unless topic itself is brand
- Not too broad
- Not too technical

--------------------------------------------------

[OUTPUT FORMAT]

Respond in JSON only:
{{"keywords": ["키워드1", "키워드2", "키워드3"]}}"""


async def extract_search_keywords(topic: str) -> List[str]:
    """
    주제 제목에서 검색 키워드 3개를 추출합니다.

    Args:
        topic: 추천 주제 제목

    Returns:
        3개의 한국어 검색 키워드 리스트. 실패 시 빈 리스트.
    """
    if not topic or not topic.strip():
        return []

    prompt = _build_keyword_prompt(topic)

    text = await call_gemini(
        prompt,
        temperature=0.3,
        max_output_tokens=256,
        timeout=30.0,
        max_retries=2,
    )

    if not text:
        logger.warning(f"[KeywordAgent] LLM 응답 없음: {topic[:50]}")
        return []

    try:
        text = text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'\s*```$', '', text)

        data = json.loads(text)
        keywords = data.get("keywords", [])

        if isinstance(keywords, list) and len(keywords) > 0:
            # 최대 3개, 문자열만 필터
            keywords = [k for k in keywords if isinstance(k, str) and k.strip()][:3]
            logger.info(f"[KeywordAgent] 키워드 추출 성공: {topic[:30]} → {keywords}")
            return keywords

        logger.warning(f"[KeywordAgent] 유효한 키워드 없음: {topic[:50]}")
        return []

    except json.JSONDecodeError as e:
        logger.error(f"[KeywordAgent] JSON 파싱 실패: {e}, text={text[:100]}")
        return []


async def extract_keywords_batch(topics: List[str]) -> List[List[str]]:
    """
    여러 주제에 대해 키워드를 일괄 추출합니다.

    Args:
        topics: 주제 제목 리스트

    Returns:
        각 주제별 키워드 리스트의 리스트
    """
    import asyncio

    if not topics:
        return []

    tasks = [extract_search_keywords(topic) for topic in topics]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    keyword_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"[KeywordAgent] 배치 추출 실패 [{i}]: {result}")
            keyword_results.append([])
        else:
            keyword_results.append(result)

    return keyword_results
