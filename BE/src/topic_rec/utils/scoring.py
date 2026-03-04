"""
Trend Scoring System

trend_score = engagement_정규화 x 소스_가중치 x 빈도_부스트
"""

from typing import List, Dict, Optional
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


def calculate_base_score(item: TrendItem) -> float:
    """engagement 정규화 x 소스 가중치"""
    source_type = get_source_type(item.source)
    weight = SOURCE_WEIGHTS.get(source_type, 0.5)
    normalized = normalize_engagement(item.engagement, source_type)
    return round(normalized * weight, 4)


def calculate_frequency_boost(
    item: TrendItem,
    global_freq: Dict[str, int],
    total_docs: int,
) -> float:
    """
    빈도 부스트 계산.

    이 아이템의 키워드가 다른 문서에서도 많이 등장할수록 부스트 증가.
    범위: 1.0 (부스트 없음) ~ 2.0 (최대 부스트)
    """
    if not item.ai_tags or not global_freq or total_docs == 0:
        return 1.0

    freqs = [
        global_freq.get(tag.lower(), 1)
        for tag in item.ai_tags
    ]
    avg_freq = sum(freqs) / len(freqs)
    freq_ratio = avg_freq / total_docs

    boost = 1.0 + freq_ratio
    return round(min(boost, 2.0), 4)


def calculate_trend_score(item: TrendItem) -> float:
    """하위 호환용 - 빈도 부스트 없이 기본 점수만"""
    return calculate_base_score(item)


def apply_trend_scores(
    items: List[TrendItem],
    global_freq: Optional[Dict[str, int]] = None,
) -> List[TrendItem]:
    """
    트렌드 스코어링.

    global_freq 있으면: engagement x 소스_가중치 x 빈도_부스트
    없으면: engagement x 소스_가중치 (하위 호환)
    """
    total_docs = len(items)

    for item in items:
        base_score = calculate_base_score(item)

        if global_freq:
            boost = calculate_frequency_boost(item, global_freq, total_docs)
            item.trend_score = round(base_score * boost, 4)
        else:
            item.trend_score = base_score

    return items


def sort_by_trend_score(items: List[TrendItem], descending: bool = True) -> List[TrendItem]:
    return sorted(items, key=lambda x: x.trend_score, reverse=descending)


def get_score_breakdown(item: TrendItem, global_freq: Optional[Dict[str, int]] = None) -> dict:
    source_type = get_source_type(item.source)
    weight = SOURCE_WEIGHTS.get(source_type, 0.5)
    normalized = normalize_engagement(item.engagement, source_type)
    total_docs = 1

    boost = 1.0
    if global_freq:
        boost = calculate_frequency_boost(item, global_freq, total_docs)

    return {
        "source_type": source_type,
        "raw_engagement": item.engagement,
        "normalized_engagement": normalized,
        "source_weight": weight,
        "frequency_boost": boost,
        "final_score": item.trend_score,
    }
