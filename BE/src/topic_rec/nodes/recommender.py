"""
Recommender Node - LLM-based 3-Type Topic Recommendation

페르소나 풀데이터 + core/adjacent 트렌드 그룹 요약을 기반으로
3가지 관점(viewer_needs, hit_pattern, channel_expansion)에서 추천합니다.
"""

import json
import re
import requests
from datetime import date
from typing import List, Dict

from app.core.config import settings
from src.topic_rec.state import TopicRecState, TopicCluster

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


RECOMMENDATION_TYPES = {
    "viewer_needs": "구독자 니즈",
    "hit_pattern": "성공방정식",
    "trend_driven": "최신경향성",
}


class LLMRecommender:
    """LLM-based recommender - 3타입 추천"""

    def __init__(self):
        self.gemini_key = settings.gemini_api_key
        self.provider = None
        self.model = None

        if self.gemini_key and HAS_GENAI:
            self.provider = "gemini"
            genai.configure(api_key=self.gemini_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash")
            print("[Recommender] Using Google Gemini")
        else:
            self.provider = "ollama"
            self.ollama_model = "llama3.2"
            print(f"[Recommender] Using Ollama ({self.ollama_model})")

    def recommend(
        self,
        clusters: List[TopicCluster],
        persona: dict,
    ) -> List[Dict]:
        if not clusters:
            return []

        trend_summary = self._build_summary(clusters[:10])
        prompt = self._build_prompt(trend_summary, persona)

        try:
            if self.provider == "gemini":
                response_obj = self.model.generate_content(prompt)
                response_text = response_obj.text
            else:
                response_text = self._call_ollama(prompt)

            return self._parse_response(response_text)

        except Exception as e:
            print(f"[Recommender] Error: {e}")
            return self._fallback(clusters)

    def _build_summary(self, clusters: List[TopicCluster]) -> str:
        """클러스터의 trend_summary를 core/adjacent로 나눠서 합침"""
        core_summaries = []
        adjacent_summaries = []

        for c in clusters:
            if c.name == "기타":
                continue

            summary = c.trend_summary if c.trend_summary else f"[{c.name}] ({c.item_count}건)"

            core_count = sum(
                1 for item in c.items
                if getattr(item, "source_layer", None) == "core"
            )
            adj_count = sum(
                1 for item in c.items
                if getattr(item, "source_layer", None) == "adjacent"
            )

            if adj_count > core_count:
                adjacent_summaries.append(summary)
            else:
                core_summaries.append(summary)

        lines = []
        if core_summaries:
            lines.append("## Core 트렌드 (채널 핵심 분야)")
            lines.extend(core_summaries)
        if adjacent_summaries:
            if lines:
                lines.append("")
            lines.append("## Adjacent 트렌드 (확장 가능 분야)")
            lines.extend(adjacent_summaries)

        return "\n\n".join(lines)

    def _build_prompt(self, trend_summary: str, persona: dict) -> str:
        persona_summary = persona.get("persona_summary", "")
        main_topics = persona.get("main_topics", [])
        target_audience = persona.get("target_audience", "일반 시청자")
        hit_patterns = persona.get("hit_patterns", [])
        audience_needs = persona.get("audience_needs", "")
        viewer_likes = persona.get("viewer_likes", [])
        tone = persona.get("tone_manner", "")
        recent_videos = persona.get("recent_video_titles", [])

        today = date.today().strftime("%Y년 %m월 %d일")

        return f"""당신은 YouTube 크리에이터를 위한 콘텐츠 전략가입니다.
트렌드 데이터와 채널 페르소나를 분석하여 영상 주제를 추천합니다.
오늘 날짜: {today}

## 채널 정보
- 채널 설명: {persona_summary if persona_summary else persona.get("channel_name", "Unknown")}
- 주요 주제: {", ".join(main_topics) if main_topics else "알 수 없음"}
- 타겟 시청자: {target_audience}
- 톤앤매너: {tone if tone else "지정 없음"}

## 채널 성공 패턴
{chr(10).join(f"- {p}" for p in hit_patterns) if hit_patterns else "- 데이터 없음"}

## 시청자 니즈
- 시청자 특성: {audience_needs if audience_needs else "데이터 없음"}
- 시청자가 좋아하는 것: {chr(10).join(f"  - {v}" for v in viewer_likes) if viewer_likes else "데이터 없음"}

## 채널의 최근 영상 (최신순)
{chr(10).join(f"- {t}" for t in recent_videos[:15]) if recent_videos else "- 데이터 없음"}

**중요: 추천 주제는 위 최근 영상의 방향성과 자연스럽게 이어져야 합니다. 채널이 최근 다루는 주제와 너무 동떨어진 추천은 하지 마세요.**

## 트렌드 데이터
{trend_summary}

## 추천 요청
아래 3가지 관점에서 각 1개씩, 총 3개의 영상 주제를 추천해주세요.
**각 추천은 반드시 서로 다른 트렌드 그룹에서 선택해야 합니다.**

### 1. viewer_needs (구독자 니즈)
- 시청자 니즈/좋아하는 것 + 지금 핫한 트렌드를 결합
- 시청자가 "이거 궁금했는데!" 할 만한 주제
- **제목 스타일**: 시청자 눈높이에 맞춘 친근한 제목

### 2. hit_pattern (성공방정식)
- 이 채널에서 잘 됐던 패턴(성공 패턴)을 트렌드와 결합
- 기존에 성공한 포맷/주제를 새 트렌드에 적용
- **제목 스타일**: 이 채널의 톤앤매너를 반영

### 3. trend_driven (최신경향성)
- 트렌드 데이터에서 지금 가장 뜨거운 주제
- 이 채널의 주요 주제 분야에서 다룰 수 있는 최신 트렌드
- 채널 확장이 아니라, 채널 분야 안에서의 최신 흐름
- **제목 스타일**: 시의성을 강조하는 제목 (숫자, 날짜, "지금" 등 활용)

각 추천에 포함할 항목:
- title: 한국어 영상 제목 (반드시 위 '채널의 최근 영상' 제목 톤과 유사한 스타일로 작성. 채널 이름은 넣지 말 것)
- recommendation_type: "viewer_needs" / "hit_pattern" / "trend_driven"
- source_layer: 주로 참고한 트렌드가 "core" / "adjacent" 중 어디인지
- based_on_topic: 어떤 트렌드 그룹 기반인지
- trend_basis: 왜 지금 핫한지 (구체적 데이터 포함)
- recommendation_reason: 왜 이 채널에 적합한지
- search_keywords: 스크립트 자료조사용 검색 키워드 (3~5개, 배열)

  [키워드 도출법]
  "이 스크립트를 쓰려면 어떤 자료가 필요하지?" 먼저 생각하고,
  그 자료를 실제로 찾을 수 있는 검색어를 도출할 것

  [금지]
  - 검색해도 결과 없을 키워드
  - 주제와 연결 약한 범용 키워드
  - 좋은 키워드가 3개뿐이면 3개만 (억지로 채우지 말 것)

- recommendation_direction: 이 영상을 어떤 방향으로 만들면 좋을지 구체적 제안 (예: "GPT-5의 달라진 점을 초보자 눈높이에서 데모 중심으로 풀어보세요")
- content_angles: 2-3개의 구체적인 콘텐츠 접근 방식
- thumbnail_idea: 썸네일 구성 아이디어
- urgency: urgent(즉시)/normal(1주내)/evergreen(상시)

## 반드시 JSON 배열만 출력 (한국어)
[{{"title":"..","recommendation_type":"viewer_needs","source_layer":"core","based_on_topic":"..","trend_basis":"..","recommendation_reason":"..","recommendation_direction":"..","search_keywords":["키워드1","키워드2","키워드3"],"content_angles":["..",".."],"thumbnail_idea":"..","urgency":"normal"}}]"""

    def _call_ollama(self, prompt: str) -> str:
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 2000,
                "temperature": 0.7,
            },
        }
        response = requests.post(url, json=payload, timeout=600)
        response.raise_for_status()
        return response.json().get("response", "")

    def _parse_response(self, response_text: str) -> List[Dict]:
        text = response_text.strip()
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)

        match = re.search(r"\[\s*\{[\s\S]*\}\s*\]", text)

        if match:
            json_str = match.group(0)
            try:
                json_str = re.sub(r",\s*\]", "]", json_str)
                json_str = re.sub(r",\s*\}", "}", json_str)

                result = json.loads(json_str)

                if isinstance(result, list):
                    valid = []
                    for item in result:
                        if isinstance(item, dict) and "title" in item:
                            # search_keywords 파싱
                            raw_keywords = item.get("search_keywords", [])
                            if isinstance(raw_keywords, list):
                                search_keywords = raw_keywords
                            elif isinstance(raw_keywords, dict):
                                search_keywords = []
                                for vals in raw_keywords.values():
                                    if isinstance(vals, list):
                                        search_keywords.extend(vals)
                                search_keywords = list(set(search_keywords))[:5]
                            else:
                                search_keywords = []

                            # recommendation_type 검증
                            rec_type = item.get("recommendation_type", "viewer_needs")
                            if rec_type not in RECOMMENDATION_TYPES:
                                rec_type = "viewer_needs"

                            valid.append({
                                "title": item.get("title", "N/A"),
                                "recommendation_type": rec_type,
                                "recommendation_type_label": RECOMMENDATION_TYPES[rec_type],
                                "source_layer": item.get("source_layer", "core"),
                                "based_on_topic": item.get("based_on_topic", "N/A"),
                                "trend_basis": item.get("trend_basis", "N/A"),
                                "recommendation_reason": item.get("recommendation_reason", "N/A"),
                                "recommendation_direction": item.get("recommendation_direction", "N/A"),
                                "search_keywords": search_keywords,
                                "content_angles": item.get("content_angles", []),
                                "thumbnail_idea": item.get("thumbnail_idea", "N/A"),
                                "urgency": item.get("urgency", "normal"),
                            })
                    if valid:
                        return valid
            except json.JSONDecodeError as e:
                print(f"[Recommender] JSON parse error: {e}")

        return self._fallback([])

    def _fallback(self, clusters: List[TopicCluster]) -> List[Dict]:
        types = ["viewer_needs", "hit_pattern", "trend_driven"]
        results = []

        for i, c in enumerate(clusters[:3]):
            if c.name == "기타":
                continue
            rec_type = types[i] if i < len(types) else "viewer_needs"
            results.append({
                "title": f"[Auto] {c.name} 트렌드 분석",
                "recommendation_type": rec_type,
                "recommendation_type_label": RECOMMENDATION_TYPES[rec_type],
                "source_layer": "core",
                "based_on_topic": c.name,
                "trend_basis": f"{c.item_count}개 항목, 점수 {c.cluster_score:.3f}",
                "recommendation_reason": "자동 생성 (LLM 실패)",
                "recommendation_direction": "자동 생성 (LLM 실패)",
                "search_keywords": c.keywords[:5],
                "content_angles": ["트렌드 요약", "심층 분석", "향후 전망"],
                "thumbnail_idea": f"{c.name} 관련 이미지",
                "urgency": "normal",
            })

        return results


def recommend_node(state: TopicRecState) -> dict:
    """
    Generate 3-type topic recommendations using LLM.

    Source Selector가 이미 채널 맞춤 데이터를 수집했으므로
    카테고리 필터링 없이 전체 클러스터를 LLM에 전달합니다.
    """
    print("[Recommender] Generating 3-type recommendations...")

    clusters = state.get("clusters", [])
    persona = state.get("persona", {})

    if not clusters:
        print("[Recommender] No clusters available")
        return {
            "recommendations": [],
            "current_step": "recommend",
            "error": "No clusters to recommend from",
        }

    print(f"[Recommender] {len(clusters)} groups available")

    recommender = LLMRecommender()
    recommendations = recommender.recommend(clusters, persona)

    print(f"[Recommender] Generated {len(recommendations)} recommendations")
    for i, rec in enumerate(recommendations, 1):
        label = rec.get("recommendation_type_label", "")
        print(f"    {i}. [{label}] {rec.get('title', 'N/A')}")

    return {
        "recommendations": recommendations,
        "current_step": "recommend",
    }
