"""
Processor Node - TF-IDF 키워드 추출 + 빈도 부스트 스코어링
"""

from src.topic_rec.state import TopicRecState
from src.topic_rec.utils.keyword_extractor import extract_keywords_tfidf
from src.topic_rec.utils.scoring import apply_trend_scores


def process_node(state: TopicRecState) -> dict:
    """
    Preprocess collected trends.

    Steps:
    1. TF-IDF 키워드 추출 (글로벌 빈도 + 문서별 고유 키워드)
    2. 스코어링 (engagement x 소스 가중치 x 빈도 부스트)
    """
    print("[Processor] Starting preprocessing...")

    trends = state.get("trends", [])

    if not trends:
        print("[Processor] No trends to process")
        return {
            "processed_trends": [],
            "current_step": "process",
            "error": "No trends collected",
        }

    # Step 1: TF-IDF 키워드 추출
    print(f"  -> Extracting keywords (TF-IDF) from {len(trends)} items...")
    trends, global_freq = extract_keywords_tfidf(trends)

    top_trending = sorted(global_freq.items(), key=lambda x: x[1], reverse=True)[:10]
    print(f"     Top trending: {', '.join(f'{kw}({cnt})' for kw, cnt in top_trending)}")

    # Step 2: 스코어링 (빈도 부스트 포함)
    print("  -> Scoring (engagement x source weight x frequency boost)...")
    trends = apply_trend_scores(trends, global_freq=global_freq)

    print(f"[Processor] Processed: {len(trends)} items")

    return {
        "processed_trends": trends,
        "current_step": "process",
    }
