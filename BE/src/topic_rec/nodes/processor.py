"""
Processor Node - Preprocessing (category mapping, keywords, scoring)
"""

from src.topic_rec.state import TopicRecState
from src.topic_rec.utils import (
    map_categories,
    map_subcategories,
    enrich_with_keywords,
    apply_trend_scores,
)


def process_node(state: TopicRecState) -> dict:
    """
    Preprocess collected trends.

    Steps:
    1. Map categories (rule-based)
    2. Extract keywords
    3. Calculate trend scores

    Note: 페르소나 기반 필터링은 여기서 하지 않음.
          전체 트렌드를 분석하고, LLM 추천 단계에서 페르소나에 맞게 추천.
    """
    print("[Processor] Starting preprocessing...")

    trends = state.get("trends", [])
    persona = state.get("persona", {})

    if not trends:
        print("[Processor] No trends to process")
        return {
            "processed_trends": [],
            "current_step": "process",
            "error": "No trends collected",
        }

    # Step 1: Category mapping (대분류)
    print("  -> Mapping categories...")
    trends = map_categories(trends)

    # Step 2: SubCategory mapping (중분류)
    print("  -> Mapping subcategories...")
    trends = map_subcategories(trends)

    # Step 3: Keyword extraction
    print("  -> Extracting keywords...")
    trends = enrich_with_keywords(trends)

    # Step 4: Trend scoring
    print("  -> Calculating scores...")
    trends = apply_trend_scores(trends)

    # 전체 트렌드를 다음 단계로 전달 (필터링은 LLM 추천 단계에서 페르소나 기반으로 처리)
    print(f"[Processor] Processed: {len(trends)} items")

    return {
        "processed_trends": trends,
        "current_step": "process",
    }
