"""
Source Selector Agent - 채널 페르소나 기반 트렌드 소스 동적 선택

페르소나 정보를 바탕으로 LLM이 Core(핵심)/Adjacent(확장) 소스를 결정합니다.
"""

import json
import re

from langchain_openai import ChatOpenAI
from app.core.config import settings
from src.topic_rec.state import TopicRecState


# LLM 실패 시 기본 매핑
DEFAULT_SOURCE_CONFIG = {
    "core": {
        "reddit": {"subreddits": [], "keywords": []},
        "google_news": ["TECHNOLOGY"],
        "hacker_news": {"use": True, "keywords": []},
        "google_trends": [],
    },
    "adjacent": {
        "reddit": {"subreddits": ["technology", "Futurology"], "keywords": []},
        "google_news": ["BUSINESS", "SCIENCE"],
        "hacker_news": {"use": False, "keywords": []},
        "google_trends": [],
    },
}


class SourceSelector:
    """채널 페르소나 기반으로 트렌드 소스를 선택하는 Agent"""

    def __init__(self):
        api_key = settings.openai_api_key
        if api_key:
            self.model = ChatOpenAI(model="gpt-4o", api_key=api_key, temperature=0.3)
            print("[SourceSelector] Using GPT-4o")
        else:
            self.model = None
            print("[SourceSelector] No OpenAI API key, will use default sources")

    def select_sources(self, persona: dict) -> dict:
        """
        페르소나를 기반으로 Core/Adjacent 소스를 선택합니다.

        Args:
            persona: 채널 페르소나 정보

        Returns:
            source_config: {"core": {...}, "adjacent": {...}}
        """
        if not self.model:
            print("[SourceSelector] No LLM available, using default config")
            return DEFAULT_SOURCE_CONFIG

        prompt = self._build_prompt(persona)

        try:
            response = self.model.invoke(prompt)
            result = self._parse_response(response.content)
            if result:
                print("[SourceSelector] LLM source selection successful")
                return result
        except Exception as e:
            print(f"[SourceSelector] LLM error: {e}")

        print("[SourceSelector] Falling back to default config")
        return DEFAULT_SOURCE_CONFIG

    def _build_prompt(self, persona: dict) -> str:
        persona_summary = persona.get("persona_summary", "Unknown")
        main_topics = persona.get("main_topics", [])
        recent_videos = persona.get("recent_video_titles", [])

        return f"""당신은 YouTube 크리에이터를 위한 트렌드 소스 선택 전문가입니다.
이 채널에 트렌드한 영상 주제를 추천하기 위해, 어떤 소스에서 어떤 키워드로 검색할지 결정합니다.

## 채널 정보
- 채널: {persona_summary}
- 주요 주제: {', '.join(main_topics) if main_topics else '알 수 없음'}

## 채널의 영상 목록 (최신순)
{chr(10).join(f'- {t}' for t in recent_videos[:50]) if recent_videos else '- 데이터 없음'}

## 분석 순서
1단계: 위 채널 정보와 영상 제목을 분석하여 이 채널의 **카테고리**와 **콘텐츠 방향성**을 파악하세요.
  - 이 채널이 속한 분야는? (예: AI 코딩 도구, 게임 리뷰, 재테크 등)
  - 최근 어떤 방향으로 콘텐츠를 만들고 있는가?
  - 시청자가 기대하는 콘텐츠는?

2단계: 파악한 방향성을 기반으로, 이 채널에 **트렌드한 영상 주제를 추천하기 위해** 아래 소스에서 무엇을 검색할지 결정하세요.

## 사용 가능한 소스

### Core (채널 핵심 트렌드) — 채널 방향성에 딱 맞는 트렌드 수집
- **Reddit keywords** (영어, 최대 5개): 채널 주제에 맞는 구체적 키워드로 Reddit 전체 검색
- **Hacker News keywords** (영어, 최대 5개): 동일한 방식으로 HN 검색
- **Google News**: 카테고리 선택 (TECHNOLOGY, BUSINESS, SCIENCE, ENTERTAINMENT, SPORTS, HEALTH, LIFESTYLE 중)
- **Google Trends** (한국어, 최대 5개): 한국 트렌드 검색 키워드

### Adjacent (확장 트렌드 발굴) — 채널의 상위 카테고리에서 새로운 트렌드 발굴
- **Reddit subreddits** (최대 3개): 채널 상위 카테고리의 대형 커뮤니티에서 전반적 트렌드 수집
- **Google News**: 카테고리 선택
- **Google Trends** (한국어, 최대 5개): 더 넓은 범위의 트렌드 키워드

## 출력 형식 (분석 결과 없이, 반드시 유효한 JSON만 출력)
{{"core":{{"reddit":{{"subreddits":[],"keywords":["kw1","kw2","kw3"]}},"google_news":["CATEGORY1"],"hacker_news":{{"use":true,"keywords":["kw1","kw2"]}},"google_trends":["키워드1","키워드2"]}},"adjacent":{{"reddit":{{"subreddits":["technology","Futurology"],"keywords":[]}},"google_news":["CATEGORY1"],"hacker_news":{{"use":false,"keywords":[]}},"google_trends":["키워드1","키워드2"]}}}}"""

    def _parse_response(self, response_text: str) -> dict | None:
        """LLM 응답에서 JSON을 추출하고 검증합니다."""
        text = response_text.strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*]", "]", text)

        try:
            result = json.loads(text.strip())
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", text)
            if not match:
                print("[SourceSelector] No JSON found in response")
                return None
            try:
                result = json.loads(match.group(0))
            except json.JSONDecodeError as e:
                print(f"[SourceSelector] JSON parse error: {e}")
                print(f"[SourceSelector] Raw response:\n{response_text[:500]}")
                return None

        # 구조 검증
        if "core" not in result or "adjacent" not in result:
            print("[SourceSelector] Missing core/adjacent in response")
            return None

        # 각 레이어 기본값 채우기
        for layer in ["core", "adjacent"]:
            cfg = result[layer]
            # reddit: list(구버전) → dict 변환
            if "reddit" not in cfg:
                cfg["reddit"] = {"subreddits": [], "keywords": []}
            elif isinstance(cfg["reddit"], list):
                cfg["reddit"] = {"subreddits": cfg["reddit"], "keywords": []}
            else:
                cfg["reddit"].setdefault("subreddits", [])
                cfg["reddit"].setdefault("keywords", [])
            if "google_news" not in cfg:
                cfg["google_news"] = []
            if "hacker_news" not in cfg:
                cfg["hacker_news"] = {"use": False, "keywords": []}
            if "google_trends" not in cfg:
                cfg["google_trends"] = []

        return result


def source_select_node(state: TopicRecState) -> dict:
    """
    LangGraph 노드: Source Selector Agent 실행.

    State에서 persona를 읽고, LLM으로 소스를 선택하여
    source_config를 State에 저장합니다.
    """
    print("[SourceSelector] Selecting trend sources...")

    persona = state.get("persona", {})
    selector = SourceSelector()
    source_config = selector.select_sources(persona)

    # 결과 로그
    core = source_config.get("core", {})
    adjacent = source_config.get("adjacent", {})
    print(f"[SourceSelector] Core - Reddit: {core.get('reddit', [])}")
    print(f"[SourceSelector] Core - News: {core.get('google_news', [])}")
    print(f"[SourceSelector] Adjacent - Reddit: {adjacent.get('reddit', [])}")
    print(f"[SourceSelector] Adjacent - News: {adjacent.get('google_news', [])}")

    return {
        "source_config": source_config,
        "current_step": "source_select",
    }
