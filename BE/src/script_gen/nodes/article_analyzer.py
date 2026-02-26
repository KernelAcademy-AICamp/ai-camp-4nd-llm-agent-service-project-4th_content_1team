"""
Article Analyzer Node - 기사 내용 심층 분석 에이전트

News Research Node가 수집한 각 기사의 본문을 읽고
중요한 팩트, 전문가 의견/해석, 핵심 포인트를 추출하여 구조화된 리스트로 정리합니다.

[역할 분리]
- news_research_node : 기사 수집 + 본문 크롤링 + 이미지 수집  (What to collect)
- article_analyzer_node : 기사 내용 분석 + 팩트/의견/핵심포인트 추출 (What to learn)

[출력 구조]
각 기사 article["analysis"]["facts"]       → 검증 가능한 팩트 리스트 (Writer 인용용)
각 기사 article["analysis"]["opinions"]    → 전문가 의견/해석 리스트
각 기사 article["analysis"]["key_points"]  → 핵심 포인트 서술 (팝업 상세보기용)
news_data["structured_facts"]              → insight_builder 호환 팩트 (ID+카테고리 포함)
news_data["structured_opinions"]           → 의견 전체 모음
"""

from typing import Dict, Any, List
import asyncio
import json
import logging
import os
import uuid

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

from src.script_gen.nodes.news_research import _extract_source_from_url

load_dotenv()

logger = logging.getLogger(__name__)

# 설정
MODEL_NAME = "gpt-4o"
MAX_CONCURRENT = 1          # 순차 처리 → news_research 이미지 분석과 TPM 충돌 방지
MAX_CONTENT_LENGTH = 6000   # 기사당 최대 분석 본문 길이 (토큰 절약)
MAX_RETRY = 4               # 429 재시도 최대 횟수
RETRY_BASE_DELAY = 5.0      # 재시도 초기 대기 시간 (초)


async def article_analyzer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    각 기사의 본문을 읽고 중요한 팩트, 의견, 핵심 포인트를 추출합니다.

    Input (state에서 읽음):
        news_data.articles : 기사 목록 (content 필드 포함, images/charts 포함)
        topic             : 영상 주제 (관련성 필터링 기준)

    Output (state에 반영):
        news_data.articles          : analysis 필드가 채워진 기사 목록
        news_data.structured_facts  : insight_builder 호환 팩트 리스트
        news_data.structured_opinions : 의견 전체 모음
    """
    logger.info("[Article Analyzer] 기사 심층 분석 시작")

    news_data = state.get("news_data", {})
    articles = news_data.get("articles", [])
    topic = state.get("topic", "")

    if not articles:
        logger.info("[Article Analyzer] 분석할 기사 없음 → 건너뜀")
        return {}

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("[Article Analyzer] OPENAI_API_KEY 없음 → 분석 건너뜀")
        return {}

    llm = ChatOpenAI(model=MODEL_NAME, api_key=api_key, temperature=0.2)

    # ------------------------------------------------------------------
    # 단일 기사 분석 함수 (asyncio.gather에서 병렬 실행)
    # ------------------------------------------------------------------
    async def analyze_single_article(article: Dict) -> Dict:
        """기사 본문 → 팩트·의견·핵심포인트 추출"""
        content = article.get("content", "")
        title = article.get("title", "")
        url = article.get("url", "")

        # 이미지 수집 정보 (news_research에서 이미 크롤링됨)
        images = article.get("images", [])
        charts = article.get("charts", [])
        has_visuals = len(images) + len(charts) > 0

        # 본문이 없거나 너무 짧으면 요약 기반 최소 팩트만 추출
        if not content or len(content) < 100:
            fallback_text = article.get("summary_short") or article.get("desc", "")
            if fallback_text and len(fallback_text) > 20:
                article["analysis"] = {
                    "facts": [fallback_text[:300]],
                    "opinions": [],
                    "key_points": [fallback_text[:200]],
                }
                logger.info(f"[Article Analyzer] 본문 부족 → 요약 기반 팩트 1개: {title[:40]}")
            else:
                article["analysis"] = article.get("analysis") or {
                    "facts": [], "opinions": [], "key_points": []
                }
                logger.info(f"[Article Analyzer] 본문 부족, 건너뜀: {title[:40]}")
            return article

        input_text = content[:MAX_CONTENT_LENGTH]

        # 이미지/차트 컨텍스트 추가 (분석 힌트 제공)
        visual_context = ""
        if has_visuals:
            visual_items = []
            for img in charts[:3]:
                desc = img.get("desc", "") or img.get("caption", "")
                if desc:
                    visual_items.append(f"[차트/표] {desc}")
            for img in images[:3]:
                desc = img.get("desc", "") or img.get("caption", "")
                if desc:
                    visual_items.append(f"[이미지] {desc}")
            if visual_items:
                visual_context = f"\n\n[기사 내 시각 자료]\n" + "\n".join(visual_items)

        prompt = f"""당신은 YouTube 크리에이터의 리서치 어시스턴트입니다.

[영상 주제]
"{topic}"

[기사 제목]
"{title}"

[기사 본문]
{input_text}{visual_context}

위 기사를 꼼꼼히 읽고, 아래 JSON 형식으로만 응답하세요 (설명 없이):

{{
  "source": "언론사/출처명 (예: 매일경제, TechCrunch, 네이버 블로그)",
  "summary_short": "기사 핵심 1문장 요약 (한국어, 40자 이내)",
  "analysis": {{
    "key_points": [
      "이 기사가 영상 주제와 관련하여 말하는 핵심 포인트 1 (서술형 완결 문장, 한국어)",
      "핵심 포인트 2",
      "핵심 포인트 3"
    ],
    "facts": [
      {{
        "content": "팩트 내용 (완결된 한 문장, 한국어)",
        "category": "Statistic | Event | Quote | Fact",
        "value": "핵심 수치·키워드 (없으면 null)"
      }}
    ],
    "opinions": [
      "[태그] 발언자/기관명: 의견 내용 (한국어)"
    ]
  }}
}}

[key_points] 3~5개 서술형, [facts] 3~6개, [opinions] 발언자 필수. JSON만 반환."""

        # ── 재시도 루프 (429 Rate Limit 대응) ──────────────────────────────
        last_error = None
        for attempt in range(MAX_RETRY):
            try:
                delay = RETRY_BASE_DELAY * (2 ** attempt)  # 지수 백오프: 5s, 10s, 20s, 40s
                if attempt > 0:
                    logger.info(
                        f"[Article Analyzer] 재시도 {attempt}/{MAX_RETRY-1} "
                        f"({delay:.0f}초 대기): {title[:40]}"
                    )
                    await asyncio.sleep(delay)

                res = await llm.ainvoke([HumanMessage(content=prompt)])
                raw = res.content.replace("```json", "").replace("```", "").strip()
                data = json.loads(raw)

                # ── 출처명 결정: URL 맵 → og:site_name → GPT 순서 ──
                url_source = _extract_source_from_url(url)
                og_source = article.get("og_source", "")
                gpt_source = data.get("source", "")

                if url_source:
                    article["source"] = url_source
                elif og_source:
                    article["source"] = og_source
                elif gpt_source and gpt_source not in ("Unknown", "미상", "출처불명", "출처 미상", ""):
                    article["source"] = gpt_source
                else:
                    article["source"] = og_source or gpt_source or "Unknown"

                # ── summary_short 업데이트 ──
                if data.get("summary_short"):
                    article["summary_short"] = data["summary_short"]

                # ── analysis 업데이트 ──
                raw_analysis = data.get("analysis", {})
                raw_facts: List = raw_analysis.get("facts", [])
                opinions: List[str] = raw_analysis.get("opinions", [])
                key_points: List[str] = raw_analysis.get("key_points", [])

                # facts 정규화 (dict → content 문자열 추출)
                normalized_facts = []
                for f in raw_facts:
                    if isinstance(f, dict):
                        normalized_facts.append(f.get("content", str(f)))
                    else:
                        normalized_facts.append(str(f))

                article["analysis"] = {
                    "key_points": key_points,
                    "facts": normalized_facts,
                    "opinions": opinions,
                    # 내부용: category/value 보존 → structured_facts 재생성에 사용
                    "_raw_facts": raw_facts,
                }

                logger.info(
                    f"[Article Analyzer] 완료: '{title[:40]}' "
                    f"→ 핵심포인트 {len(key_points)}개, 팩트 {len(normalized_facts)}개, "
                    f"의견 {len(opinions)}개, 이미지 {len(images)+len(charts)}개"
                )
                last_error = None
                break  # 성공 → 루프 탈출

            except json.JSONDecodeError as e:
                logger.warning(f"[Article Analyzer] JSON 파싱 실패 ({title[:40]}): {e}")
                last_error = e
                break  # JSON 에러는 재시도해도 의미 없음
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "rate_limit" in err_str.lower():
                    logger.warning(
                        f"[Article Analyzer] Rate limit 429 ({title[:40]}) "
                        f"→ attempt {attempt+1}/{MAX_RETRY}"
                    )
                    last_error = e
                    continue  # 재시도
                else:
                    logger.warning(f"[Article Analyzer] 분석 실패 ({title[:40]}): {e}")
                    last_error = e
                    break  # 다른 에러는 재시도 안 함

        if last_error:
            logger.warning(f"[Article Analyzer] 최종 실패 ({title[:40]}): {last_error}")
            # 실패 시 기본 analysis 설정 (상세보기 UI용)
            article["analysis"] = article.get("analysis") or {
                "facts": [],
                "opinions": [],
                "key_points": [],
            }
            fallback_summary = article.get("summary_short") or article.get("desc", "")
            if fallback_summary and len(fallback_summary) > 20:
                article["analysis"]["facts"] = [fallback_summary[:300]]
                article["analysis"]["key_points"] = [fallback_summary[:200]]

        return article

    # ------------------------------------------------------------------
    # 세마포어로 동시 실행 수 제한하면서 병렬 분석
    # ------------------------------------------------------------------
    logger.info(
        f"[Article Analyzer] {len(articles)}개 기사 병렬 분석 시작 "
        f"(concurrent={MAX_CONCURRENT})"
    )

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def analyze_with_semaphore(article: Dict) -> Dict:
        async with semaphore:
            return await analyze_single_article(article)

    analyzed_articles = await asyncio.gather(
        *[analyze_with_semaphore(art) for art in articles]
    )

    # ------------------------------------------------------------------
    # structured_facts / structured_opinions 재생성
    # (insight_builder 및 worker.py 호환 형식)
    # ------------------------------------------------------------------
    structured_facts: List[Dict] = []
    structured_opinions: List[str] = []

    for i, art in enumerate(analyzed_articles):
        source_name = (
            _extract_source_from_url(art.get("url", ""))
            or art.get("source", "Unknown")
        )
        article_id = art.get("id", "")
        article_url = art.get("url", "")
        analysis = art.get("analysis", {})

        raw_facts: List = analysis.get("_raw_facts", [])
        fact_texts: List[str] = analysis.get("facts", [])

        # ── 팩트 → structured_facts ──
        for j, fact_text in enumerate(fact_texts):
            raw_fact = raw_facts[j] if j < len(raw_facts) else {}
            category = (
                raw_fact.get("category", "Fact")
                if isinstance(raw_fact, dict)
                else "Fact"
            )
            value = (
                raw_fact.get("value") if isinstance(raw_fact, dict) else None
            )

            structured_facts.append({
                "id": f"fact-{uuid.uuid4().hex[:12]}",
                "content": fact_text,
                "category": category,           # Statistic / Event / Quote / Fact
                "value": value or "N/A",
                "visual_proposal": "None",
                "source_index": i,
                "source_name": source_name,
                "source_indices": [i],
                "article_id": article_id,
                "article_url": article_url,
            })

        # ── 의견 → structured_opinions ──
        for op in analysis.get("opinions", []):
            structured_opinions.append(f"[{source_name}] {op}")

        # _raw_facts 제거 (직렬화 정리)
        if "_raw_facts" in art.get("analysis", {}):
            del art["analysis"]["_raw_facts"]

    logger.info(
        f"[Article Analyzer] 분석 완료: "
        f"기사 {len(analyzed_articles)}개, "
        f"팩트 {len(structured_facts)}개, "
        f"의견 {len(structured_opinions)}개"
    )

    return {
        "news_data": {
            **news_data,
            "articles": list(analyzed_articles),
            "structured_facts": structured_facts,
            "structured_opinions": structured_opinions,
        }
    }
