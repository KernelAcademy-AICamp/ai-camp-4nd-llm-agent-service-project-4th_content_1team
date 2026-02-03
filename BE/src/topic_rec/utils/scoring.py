"""
Trend Scoring System
"""

from typing import List
from src.topic_rec.state import TrendItem

SOURCE_WEIGHTS = {
    "reddit": 1.0,
    "hackernews": 0.95,
    "youtube": 0.85,
    "google_news": 0.5,
    "google_trends": 0.3,
}

MAX_ENGAGEMENT = {
    "reddit": 50000,
    "hackernews": 500,
    "youtube": 1000000,
    "google_news": 100,
    "google_trends": 1000000,
}


def get_source_type(source: str) -> str:
    return source.split('/')[0]


def normalize_engagement(engagement: int, source_type: str) -> float:
    max_val = MAX_ENGAGEMENT.get(source_type, 10000)
    normalized = min(engagement / max_val, 1.0)
    return round(normalized, 4)


def calculate_trend_score(item: TrendItem) -> float:
    source_type = get_source_type(item.source)
    weight = SOURCE_WEIGHTS.get(source_type, 0.5)
    normalized = normalize_engagement(item.engagement, source_type)
    score = normalized * weight
    return round(score, 4)


def apply_trend_scores(items: List[TrendItem]) -> List[TrendItem]:
    for item in items:
        item.trend_score = calculate_trend_score(item)
    return items


def sort_by_trend_score(items: List[TrendItem], descending: bool = True) -> List[TrendItem]:
    return sorted(items, key=lambda x: x.trend_score, reverse=descending)


def get_score_breakdown(item: TrendItem) -> dict:
    source_type = get_source_type(item.source)
    weight = SOURCE_WEIGHTS.get(source_type, 0.5)
    normalized = normalize_engagement(item.engagement, source_type)

    return {
        "source_type": source_type,
        "raw_engagement": item.engagement,
        "normalized_engagement": normalized,
        "source_weight": weight,
        "final_score": item.trend_score,
    }
