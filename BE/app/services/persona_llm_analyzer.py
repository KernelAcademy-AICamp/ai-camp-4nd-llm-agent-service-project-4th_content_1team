"""
페르소나 LLM 기반 해석

Gemini API를 사용하여 채널 콘텐츠를 분석합니다.

해석 3가지:
1. 영상 제목 분석 → 주제, 패턴, 스타일
2. 히트 vs 저조 영상 비교 → 성공 요인, 피해야 할 방향
3. 채널 설명 분석 → 정체성, 브랜딩 수준
"""
import json
from typing import List, Optional
from dataclasses import dataclass, asdict

import httpx

from app.core.config import settings


# Gemini API 설정
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"


@dataclass
class TitleAnalysisResult:
    """영상 제목 분석 결과"""
    content_topics: List[str]    # 주로 다루는 주제 (상위 5개)
    title_patterns: List[str]    # 자주 쓰는 제목 패턴
    title_style: str             # 정보형/감성형/낚시형/질문형
    interpretation: str          # 콘텐츠 성격 2~3문장


@dataclass
class HitVsLowResult:
    """히트 vs 저조 영상 비교 결과"""
    hit_factors: List[str]       # 히트 영상 공통점
    low_factors: List[str]       # 저조 영상 공통점
    success_formula: str         # 잘 되는 콘텐츠 특징
    avoid_topics: List[str]      # 피해야 할 방향


@dataclass
class DescriptionAnalysisResult:
    """채널 설명 분석 결과"""
    channel_identity: str        # 지향하는 정체성
    professionalism: str         # 브랜딩 의식 수준 (high/medium/low)
    target_impression: str       # 주고 싶어하는 인상


async def _call_gemini(prompt: str, api_key: str) -> Optional[str]:
    """Gemini API 호출."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{GEMINI_API_URL}?key={api_key}",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 2048,
                },
            },
        )

        if resp.status_code != 200:
            print(f"Gemini API error: {resp.status_code} - {resp.text}")
            return None

        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            return None


def _parse_json_response(text: str) -> Optional[dict]:
    """JSON 응답 파싱 (마크다운 코드블록 처리)."""
    if not text:
        return None

    # 코드블록 제거
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# =============================================================================
# 1. 영상 제목 분석
# =============================================================================

async def analyze_video_titles(titles: List[str]) -> Optional[TitleAnalysisResult]:
    """
    영상 제목 50개를 분석하여 콘텐츠 특성 파악.

    Args:
        titles: 최근 영상 제목 목록 (최대 50개)

    Returns:
        TitleAnalysisResult or None
    """
    api_key = settings.gemini_api_key
    if not api_key:
        print("GEMINI_API_KEY not set")
        return None

    if not titles:
        return None

    titles_text = "\n".join(f"- {t}" for t in titles[:50])

    prompt = f"""다음은 한 유튜브 채널의 최근 영상 제목 목록입니다.
이 제목들을 분석하여 채널의 콘텐츠 특성을 파악해주세요.

## 영상 제목 목록
{titles_text}

## 분석 요청
다음 JSON 형식으로 응답해주세요:

```json
{{
    "content_topics": ["주제1", "주제2", "주제3", "주제4", "주제5"],
    "title_patterns": ["패턴1 (~하는 법)", "패턴2 (N가지 팁)", "패턴3"],
    "title_style": "정보형|감성형|낚시형|질문형|혼합형 중 하나",
    "interpretation": "이 채널은 ... (2~3문장으로 콘텐츠 성격 설명)"
}}
```

분석 기준:
- content_topics: 제목에서 자주 등장하는 핵심 주제/키워드 상위 5개
- title_patterns: 자주 사용되는 제목 구조나 패턴 (예: "~하는 법", "N가지 ~", "~인 이유")
- title_style: 전반적인 제목 스타일
  - 정보형: 교육적, 설명적 ("~하는 방법", "~완벽 정리")
  - 감성형: 감정 호소, 스토리텔링 ("~했더니 인생이 바뀌었다")
  - 낚시형: 궁금증 유발, 자극적 ("충격! ~", "절대 하지 마세요")
  - 질문형: 질문으로 시작 ("~할까요?", "왜 ~일까?")
- interpretation: 종합적인 채널 콘텐츠 성격 설명
"""

    response = await _call_gemini(prompt, api_key)
    data = _parse_json_response(response)

    if not data:
        return None

    return TitleAnalysisResult(
        content_topics=data.get("content_topics", []),
        title_patterns=data.get("title_patterns", []),
        title_style=data.get("title_style", "혼합형"),
        interpretation=data.get("interpretation", ""),
    )


# =============================================================================
# 2. 히트 vs 저조 영상 비교
# =============================================================================

@dataclass
class VideoInfo:
    """영상 정보"""
    title: str
    view_count: int
    like_count: int


async def analyze_hit_vs_low(
    hit_videos: List[VideoInfo],
    low_videos: List[VideoInfo],
) -> Optional[HitVsLowResult]:
    """
    히트 영상과 저조 영상을 비교 분석.

    Args:
        hit_videos: 상위 10% 영상 (조회수 기준)
        low_videos: 하위 20% 영상 (조회수 기준)

    Returns:
        HitVsLowResult or None
    """
    api_key = settings.gemini_api_key
    if not api_key:
        return None

    if not hit_videos or not low_videos:
        return None

    hit_text = "\n".join(
        f"- {v.title} (조회수: {v.view_count:,})"
        for v in hit_videos[:10]
    )
    low_text = "\n".join(
        f"- {v.title} (조회수: {v.view_count:,})"
        for v in low_videos[:10]
    )

    prompt = f"""다음은 한 유튜브 채널의 히트 영상과 저조 영상 목록입니다.
두 그룹을 비교 분석하여 성공 요인과 피해야 할 방향을 파악해주세요.

## 히트 영상 (상위 10%)
{hit_text}

## 저조 영상 (하위 20%)
{low_text}

## 분석 요청
다음 JSON 형식으로 응답해주세요:

```json
{{
    "hit_factors": ["히트 요인1", "히트 요인2", "히트 요인3"],
    "low_factors": ["저조 요인1", "저조 요인2", "저조 요인3"],
    "success_formula": "이 채널에서 잘 되는 콘텐츠는 ... (1~2문장)",
    "avoid_topics": ["피해야 할 주제/방향1", "피해야 할 주제/방향2"]
}}
```

분석 기준:
- hit_factors: 히트 영상들의 공통점 (주제, 제목 스타일, 시의성 등)
- low_factors: 저조 영상들의 공통점 (왜 안 됐을까?)
- success_formula: 이 채널의 성공 공식 요약
- avoid_topics: 앞으로 피하거나 개선해야 할 방향
"""

    response = await _call_gemini(prompt, api_key)
    data = _parse_json_response(response)

    if not data:
        return None

    return HitVsLowResult(
        hit_factors=data.get("hit_factors", []),
        low_factors=data.get("low_factors", []),
        success_formula=data.get("success_formula", ""),
        avoid_topics=data.get("avoid_topics", []),
    )


# =============================================================================
# 3. 채널 설명 분석
# =============================================================================

async def analyze_channel_description(
    description: str,
    channel_title: str = "",
) -> Optional[DescriptionAnalysisResult]:
    """
    채널 설명을 분석하여 정체성과 브랜딩 수준 파악.

    Args:
        description: 채널 설명 텍스트
        channel_title: 채널명 (참고용)

    Returns:
        DescriptionAnalysisResult or None
    """
    api_key = settings.gemini_api_key
    if not api_key:
        return None

    if not description or len(description.strip()) < 10:
        # 설명이 너무 짧으면 분석 불가
        return DescriptionAnalysisResult(
            channel_identity="채널 설명이 없어 정체성을 파악하기 어렵습니다.",
            professionalism="low",
            target_impression="알 수 없음",
        )

    prompt = f"""다음은 유튜브 채널의 정보입니다.
채널 설명을 분석하여 채널의 정체성과 브랜딩 수준을 파악해주세요.

## 채널명
{channel_title or "(없음)"}

## 채널 설명
{description}

## 분석 요청
다음 JSON 형식으로 응답해주세요:

```json
{{
    "channel_identity": "이 채널이 지향하는 정체성을 1~2문장으로 설명",
    "professionalism": "high|medium|low 중 하나",
    "target_impression": "시청자에게 주고 싶어하는 인상을 1문장으로 설명"
}}
```

분석 기준:
- channel_identity: 채널이 스스로를 어떻게 정의하고 있는지
- professionalism: 브랜딩 의식 수준
  - high: 명확한 브랜드 메시지, 전문적인 톤, SNS/사업 연결
  - medium: 어느 정도 정돈됨, 기본적인 소개
  - low: 설명이 없거나 임시적, 브랜딩 의식 낮음
- target_impression: 시청자에게 어떤 인상을 주고 싶어하는지
"""

    response = await _call_gemini(prompt, api_key)
    data = _parse_json_response(response)

    if not data:
        return None

    return DescriptionAnalysisResult(
        channel_identity=data.get("channel_identity", ""),
        professionalism=data.get("professionalism", "medium"),
        target_impression=data.get("target_impression", ""),
    )


# =============================================================================
# 4. 카테고리 분류
# =============================================================================

# 주제 추천에서 사용하는 카테고리 목록
AVAILABLE_CATEGORIES = [
    "Technology",
    "Economy",
    "Society",
    "Entertainment",
    "Education",
    "Lifestyle",
    "Sports",
    "Science",
]

AVAILABLE_SUBCATEGORIES = {
    "Technology": ["AI", "Hardware", "Software", "Mobile", "Gaming", "Security"],
    "Economy": ["Finance", "Investment", "Crypto", "Business", "Startups"],
    "Society": ["Politics", "Environment", "Culture", "News"],
    "Entertainment": ["Music", "Movies", "Drama", "Celebrity", "Comedy"],
    "Education": ["Programming", "Career", "Language", "Study", "Self-development"],
    "Lifestyle": ["Health", "Food", "Travel", "Fashion", "Interior"],
    "Sports": ["Football", "Baseball", "Basketball", "Fitness", "Esports"],
    "Science": ["Space", "Biology", "Physics", "Medicine", "Psychology"],
}


@dataclass
class CategoryAnalysisResult:
    """카테고리 분류 결과"""
    categories: List[str]        # 메인 카테고리 (1~3개)
    subcategories: List[str]     # 서브 카테고리 (2~5개)
    reasoning: str               # 분류 근거


async def analyze_channel_categories(
    titles: List[str],
    channel_description: str = "",
) -> Optional[CategoryAnalysisResult]:
    """
    채널의 콘텐츠를 분석하여 카테고리 분류.

    Args:
        titles: 영상 제목 목록
        channel_description: 채널 설명

    Returns:
        CategoryAnalysisResult or None
    """
    api_key = settings.gemini_api_key
    if not api_key:
        print("GEMINI_API_KEY not set")
        return None

    if not titles:
        return None

    titles_text = "\n".join(f"- {t}" for t in titles[:30])

    # 서브카테고리 목록 생성
    subcategories_text = "\n".join(
        f"- {cat}: {', '.join(subs)}"
        for cat, subs in AVAILABLE_SUBCATEGORIES.items()
    )

    prompt = f"""다음은 유튜브 채널의 영상 제목과 설명입니다.
이 채널이 어떤 카테고리에 속하는지 분류해주세요.

## 영상 제목 (최근 30개)
{titles_text}

## 채널 설명
{channel_description or "(없음)"}

## 사용 가능한 카테고리
메인 카테고리: {', '.join(AVAILABLE_CATEGORIES)}

서브 카테고리:
{subcategories_text}

## 분석 요청
다음 JSON 형식으로 응답해주세요:

```json
{{
    "categories": ["Technology", "Education"],
    "subcategories": ["Programming", "AI", "Career"],
    "reasoning": "이 채널은 ... 때문에 위 카테고리로 분류됩니다."
}}
```

규칙:
- categories: 가장 적합한 메인 카테고리 1~3개 선택 (위 목록에서만)
- subcategories: 가장 적합한 서브 카테고리 2~5개 선택 (위 목록에서만)
- reasoning: 왜 이 카테고리로 분류했는지 1~2문장
- 반드시 위에 제시된 카테고리/서브카테고리 목록에서만 선택
"""

    response = await _call_gemini(prompt, api_key)
    data = _parse_json_response(response)

    if not data:
        return None

    # 유효한 카테고리만 필터링
    categories = [c for c in data.get("categories", []) if c in AVAILABLE_CATEGORIES]
    all_valid_subs = []
    for subs in AVAILABLE_SUBCATEGORIES.values():
        all_valid_subs.extend(subs)
    subcategories = [s for s in data.get("subcategories", []) if s in all_valid_subs]

    return CategoryAnalysisResult(
        categories=categories or ["Technology"],  # 기본값
        subcategories=subcategories or ["AI"],    # 기본값
        reasoning=data.get("reasoning", ""),
    )


# =============================================================================
# 종합 함수
# =============================================================================

async def get_all_llm_interpretations(
    titles: List[str],
    hit_videos: List[VideoInfo],
    low_videos: List[VideoInfo],
    channel_description: str,
    channel_title: str = "",
) -> dict:
    """
    모든 LLM 기반 해석을 실행.

    Returns:
        {
            "title_analysis": TitleAnalysisResult or None,
            "hit_vs_low": HitVsLowResult or None,
            "description_analysis": DescriptionAnalysisResult or None,
        }
    """
    # 병렬로 실행해도 되지만, API 부담 고려해서 순차 실행
    title_result = await analyze_video_titles(titles)
    hit_low_result = await analyze_hit_vs_low(hit_videos, low_videos)
    desc_result = await analyze_channel_description(channel_description, channel_title)

    return {
        "title_analysis": asdict(title_result) if title_result else None,
        "hit_vs_low": asdict(hit_low_result) if hit_low_result else None,
        "description_analysis": asdict(desc_result) if desc_result else None,
    }
