"""
Recommender Node - LLM-based Topic Recommendation

페르소나의 preferred_categories/subcategories를 기반으로
계층 구조 클러스터에서 관련 트렌드를 필터링하여 추천합니다.
"""

import json
import re
import requests
from typing import List, Dict

from app.core.config import settings
from src.topic_rec.state import (
    TopicRecState, TopicCluster, Recommendation,
    CategoryCluster, SubCategoryCluster,
)

# Optional: Google GenAI
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


# Persona presets
PERSONA_PRESETS = {
    "tech_kr": {
        "channel_name": "TechExplorer KR",
        "topic": "IT Device & Tech News",
        "target_audience": "Tech enthusiasts, Early adopters",
        "style": "Deep analysis, comparison reviews, easy explanations",
        "preferred_categories": ["Technology"],
        "preferred_subcategories": ["AI", "Hardware", "Software"],
    },
    "ai_dev_kr": {
        "channel_name": "AI Developer Korea",
        "topic": "AI/ML Development & News",
        "target_audience": "AI engineers, ML researchers, developers",
        "style": "Technical deep-dive, code examples, paper reviews",
        "preferred_categories": ["Technology"],
        "preferred_subcategories": ["AI", "Software"],
    },
    "finance_kr": {
        "channel_name": "MoneyTalk",
        "topic": "Investment & Financial News",
        "target_audience": "Workers in 20-40s, investment beginners",
        "style": "Easy explanations, practical advice",
        "preferred_categories": ["Economy"],
        "preferred_subcategories": ["Finance", "Investment", "Crypto"],
    },
    "general_kr": {
        "channel_name": "IssuePick",
        "topic": "Daily Hot Issues & Trends",
        "target_audience": "General Korean audience",
        "style": "Fast information delivery, fun editing",
        "preferred_categories": ["Society", "Entertainment", "Technology"],
        "preferred_subcategories": [],  # 전체 서브카테고리
    }
}


class LLMRecommender:
    """LLM-based recommender supporting Ollama and Gemini"""

    def __init__(self):
        self.ollama_model = "llama3.2"
        self.gemini_key = settings.gemini_api_key

        self.provider = None
        self.model = None

        if self.gemini_key and HAS_GENAI:
            self.provider = "gemini"
            genai.configure(api_key=self.gemini_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
            print("[Recommender] Using Google Gemini")
        else:
            self.provider = "ollama"
            print(f"[Recommender] Using Ollama ({self.ollama_model})")

    def recommend(
        self,
        clusters: List[TopicCluster],
        persona: dict,
        top_n: int = 3
    ) -> List[Dict]:

        if not clusters:
            return []

        cluster_summary = self._build_summary(clusters[:5])
        prompt = self._build_prompt(cluster_summary, persona, top_n)

        try:
            if self.provider == "ollama":
                response_text = self._call_ollama(prompt)
            else:
                response_obj = self.model.generate_content(prompt)
                response_text = response_obj.text

            return self._parse_response(response_text, clusters)

        except Exception as e:
            print(f"[Recommender] Error: {e}")
            return self._fallback(clusters, top_n)

    def _build_summary(self, clusters: List[TopicCluster]) -> str:
        lines = []
        for c in clusters:
            top_items = sorted(c.items, key=lambda x: x.trend_score, reverse=True)[:2]
            items_str = " / ".join([item.title[:40] for item in top_items])
            urgency = "URGENT" if c.avg_score > 0.05 else "Normal"

            lines.append(
                f"[{c.name}] {c.item_count} items, score:{c.cluster_score:.3f} {urgency}\n"
                f"  Keywords: {', '.join(c.keywords[:5])}\n"
                f"  Top: {items_str}"
            )
        return "\n\n".join(lines)

    def _build_prompt(self, cluster_summary: str, persona: dict, top_n: int) -> str:
        # 채널 스타일 결정
        channel_style = persona.get('content_style', '')
        preferred_cats = persona.get('preferred_categories', [])

        # 카테고리 기반 스타일 가이드
        style_guide = "정보 전달 중심의 명확한 제목"  # 기본값
        if any(cat in ['entertainment', 'gaming', 'Entertainment', 'Gaming'] for cat in preferred_cats):
            style_guide = "호기심을 유발하는 재미있는 제목"
        elif any(cat in ['education', 'Education', 'technology', 'Technology'] for cat in preferred_cats):
            style_guide = "정보 전달 중심의 명확하고 신뢰감 있는 제목"
        elif any(cat in ['business', 'Business', 'finance', 'Finance'] for cat in preferred_cats):
            style_guide = "전문성이 느껴지는 구체적인 제목"

        return f"""You are a YouTube content strategist for Korean creators. Recommend video topics.

## Channel Info
- Name: {persona.get('channel_name', 'Unknown')}
- Category: {', '.join(preferred_cats) if preferred_cats else 'General'}
- Target: {persona.get('target_audience', 'General audience')}
- Style: {channel_style if channel_style else 'Not specified'}

## This Week's Trends
{cluster_summary}

## Request
Recommend {top_n} topics. For each provide:
- title: 한국어, {style_guide}
- based_on_topic: 어떤 트렌드 기반인지
- trend_basis: 왜 지금 핫한지 (구체적 데이터 포함)
- recommendation_reason: 왜 이 채널에 적합한지
- search_keywords: 스크립트 자료조사용 검색 키워드 (3~5개, 배열)

  [키워드 도출법]
  "이 스크립트를 쓰려면 어떤 자료가 필요하지?" 먼저 생각하고,
  그 자료를 실제로 찾을 수 있는 검색어를 도출할 것

  [좋은 키워드 기준]
  1. 실제 검색 시 관련 영상/기사/자료가 충분히 존재함
  2. 검색 결과가 이 스크립트 작성에 직접 도움됨
  3. 너무 광범위하지 않고 적절히 구체적임

  [금지]
  - 검색해도 결과 없을 키워드
  - 주제와 연결 약한 범용 키워드
  - 개수 채우기용 filler

  [참고]
  - title에 있는 핵심 개념 포함
  - 좋은 키워드가 3개뿐이면 3개만 (억지로 채우지 말 것)

- content_angles: 2-3개의 구체적인 콘텐츠 접근 방식
- thumbnail_idea: 썸네일 구성 아이디어
- urgency: urgent(즉시)/normal(1주내)/evergreen(상시)

## Respond in JSON only (Korean)
[{{"title":"..","based_on_topic":"..","trend_basis":"..","recommendation_reason":"..","search_keywords":["키워드1","키워드2","키워드3"],"content_angles":["..",".."],"thumbnail_idea":"..","urgency":"urgent"}}]"""

    def _call_ollama(self, prompt: str) -> str:
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 1500,
                "temperature": 0.7,
            }
        }
        response = requests.post(url, json=payload, timeout=600)
        response.raise_for_status()
        return response.json().get("response", "")

    def _parse_response(self, response_text: str, clusters: List[TopicCluster]) -> List[Dict]:
        text = response_text.strip()
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)

        match = re.search(r'\[\s*\{[\s\S]*\}\s*\]', text)

        if match:
            json_str = match.group(0)
            try:
                json_str = re.sub(r',\s*\]', ']', json_str)
                json_str = re.sub(r',\s*\}', '}', json_str)

                result = json.loads(json_str)

                if isinstance(result, list):
                    valid = []
                    for item in result:
                        if isinstance(item, dict) and "title" in item:
                            # search_keywords 파싱 (단순 배열 형식)
                            raw_keywords = item.get("search_keywords", [])

                            # 배열이면 그대로, 객체면 모든 값 합쳐서 배열로
                            if isinstance(raw_keywords, list):
                                search_keywords = raw_keywords
                            elif isinstance(raw_keywords, dict):
                                # 레거시 호환: 객체면 모든 키워드 합침
                                search_keywords = []
                                for key in ["youtube_main", "youtube_reference", "google_news", "google_research", "youtube", "google"]:
                                    search_keywords.extend(raw_keywords.get(key, []))
                                search_keywords = list(set(search_keywords))[:5]  # 중복 제거 후 최대 5개
                            else:
                                search_keywords = []

                            valid.append({
                                "title": item.get("title", "N/A"),
                                "based_on_topic": item.get("based_on_topic", "N/A"),
                                "trend_basis": item.get("trend_basis", "N/A"),
                                "recommendation_reason": item.get("recommendation_reason", "N/A"),
                                "search_keywords": search_keywords,
                                "content_angles": item.get("content_angles", []),
                                "thumbnail_idea": item.get("thumbnail_idea", "N/A"),
                                "urgency": item.get("urgency", "normal"),
                            })
                    if valid:
                        return valid
            except json.JSONDecodeError as e:
                print(f"[Recommender] JSON parse error: {e}")

        return self._fallback(clusters, 3)

    def _fallback(self, clusters: List[TopicCluster], top_n: int) -> List[Dict]:
        results = []
        for c in clusters[:top_n]:
            if c.name == "Other":
                continue
            results.append({
                "title": f"[Auto] {c.name} 트렌드 분석",
                "based_on_topic": c.name,
                "trend_basis": f"{c.item_count}개 항목, 점수 {c.cluster_score:.3f}",
                "recommendation_reason": "자동 생성 (LLM 실패)",
                "search_keywords": c.keywords[:5],  # 단순 배열로 변경
                "content_angles": ["트렌드 요약", "심층 분석", "향후 전망"],
                "thumbnail_idea": f"{c.name} 관련 이미지",
                "urgency": "normal",
            })
        return results[:top_n]


def filter_clusters_by_persona(
    category_clusters: List[CategoryCluster],
    clusters: List[TopicCluster],
    persona: dict
) -> List[TopicCluster]:
    """
    페르소나의 preferred_categories/subcategories에 맞는 클러스터만 필터링합니다.
    """
    preferred_cats = persona.get("preferred_categories", [])
    preferred_subs = persona.get("preferred_subcategories", [])

    if not preferred_cats:
        return clusters  # 카테고리 제한 없음

    # category_clusters가 있으면 계층 구조 기반으로 필터링
    if category_clusters:
        filtered_items = []

        for cat_cluster in category_clusters:
            if cat_cluster.category not in preferred_cats:
                continue

            for sub_cluster in cat_cluster.sub_categories:
                # 서브카테고리 필터링 (비어있으면 전체)
                if preferred_subs and sub_cluster.sub_category not in preferred_subs:
                    continue
                filtered_items.extend(sub_cluster.items)

        # 필터링된 아이템들이 속한 클러스터만 반환
        if filtered_items:
            filtered_item_ids = {id(item) for item in filtered_items}
            filtered_clusters = []

            for cluster in clusters:
                matching_items = [item for item in cluster.items if id(item) in filtered_item_ids]
                if matching_items:
                    # 클러스터 복사 후 필터링된 아이템만 유지
                    filtered_cluster = TopicCluster(
                        cluster_id=cluster.cluster_id,
                        name=cluster.name,
                        keywords=cluster.keywords,
                        items=matching_items,
                        item_count=len(matching_items),
                        total_engagement=sum(item.engagement for item in matching_items),
                        avg_score=sum(item.trend_score for item in matching_items) / len(matching_items) if matching_items else 0,
                        cluster_score=cluster.cluster_score,
                        source_distribution=cluster.source_distribution,
                        trend_summary=cluster.trend_summary,
                        rank=cluster.rank,
                    )
                    filtered_clusters.append(filtered_cluster)

            if filtered_clusters:
                return sorted(filtered_clusters, key=lambda c: c.cluster_score, reverse=True)

    # Fallback: 기존 방식 - 클러스터 내 아이템의 카테고리로 필터링
    filtered = []
    for cluster in clusters:
        cat_match = any(
            item.ai_category in preferred_cats
            for item in cluster.items
        )
        if cat_match:
            filtered.append(cluster)

    return filtered if filtered else clusters[:5]


def recommend_node(state: TopicRecState) -> dict:
    """
    Generate topic recommendations using LLM.

    페르소나 기반으로 클러스터를 필터링한 후 LLM 추천을 생성합니다.
    """
    print("[Recommender] Generating recommendations...")

    clusters = state.get("clusters", [])
    category_clusters = state.get("category_clusters", [])
    persona = state.get("persona", PERSONA_PRESETS["tech_kr"])

    if not clusters:
        print("[Recommender] No clusters available")
        return {
            "recommendations": [],
            "current_step": "recommend",
            "error": "No clusters to recommend from",
        }

    # 페르소나 기반 필터링
    preferred_cats = persona.get("preferred_categories", [])
    preferred_subs = persona.get("preferred_subcategories", [])
    print(f"[Recommender] Filtering for: {preferred_cats} / {preferred_subs}")

    filtered_clusters = filter_clusters_by_persona(category_clusters, clusters, persona)
    print(f"[Recommender] Filtered clusters: {len(filtered_clusters)} / {len(clusters)}")

    recommender = LLMRecommender()
    recommendations = recommender.recommend(filtered_clusters, persona, top_n=3)

    print(f"[Recommender] Generated {len(recommendations)} recommendations")
    for i, rec in enumerate(recommendations, 1):
        print(f"    {i}. {rec.get('title', 'N/A')}")

    return {
        "recommendations": recommendations,
        "current_step": "recommend",
    }
