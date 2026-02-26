"""
Source Selector Agent - 채널 페르소나 기반 트렌드 소스 동적 선택

페르소나 정보를 바탕으로 LLM이 Core(핵심)/Adjacent(확장) 소스를 결정합니다.
"""

import json
import re

from app.core.config import settings
from src.topic_rec.state import TopicRecState

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


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
        self.gemini_key = settings.gemini_api_key

        if self.gemini_key and HAS_GENAI:
            genai.configure(api_key=self.gemini_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash")
            print("[SourceSelector] Using Google Gemini")
        else:
            self.model = None
            print("[SourceSelector] No Gemini API key, will use default sources")

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
            response = self.model.generate_content(prompt)
            result = self._parse_response(response.text)
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

## 채널 정보
- 채널: {persona_summary}
- 주요 주제: {', '.join(main_topics) if main_topics else '알 수 없음'}

## 채널의 최근 영상 (최신순)
{chr(10).join(f'- {t}' for t in recent_videos[:15]) if recent_videos else '- 데이터 없음'}

## 트렌드 소스 구조

### Core (채널 핵심 트렌드)
최근 영상의 동일/하위 카테고리에서 **채널 방향성에 딱 맞는** 트렌드를 수집합니다.
- **Reddit keywords** (영어, 최대 5개): 채널 주제에 맞는 구체적 키워드로 Reddit 전체 검색
  예: 바이브코딩 채널 → "AI coding", "Cursor AI", "vibe coding", "code generation", "AI agent"
- **Hacker News keywords** (영어, 최대 5개): 동일한 방식으로 HN 검색
- **Google News**: 카테고리 선택 (TECHNOLOGY, BUSINESS, SCIENCE, ENTERTAINMENT, SPORTS, HEALTH, LIFESTYLE 중)
- **Google Trends** (한국어, 최대 5개): 한국 트렌드 검색 키워드

### Adjacent (확장 트렌드 발굴)
채널의 상위 카테고리에서 **새로운 트렌드를 발굴**합니다.
- **Reddit subreddits** (최대 3개): 넓은 대형 커뮤니티에서 전반적 트렌드 수집
  예: 바이브코딩 채널 → technology, programming, Futurology
  (채널 주제의 상위 카테고리에 해당하는 대형 서브레딧)
- **Google News**: 카테고리 선택
- **Google Trends** (한국어, 최대 5개): 더 넓은 범위의 트렌드 키워드

## 출력 형식 (반드시 유효한 JSON만 출력)
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
