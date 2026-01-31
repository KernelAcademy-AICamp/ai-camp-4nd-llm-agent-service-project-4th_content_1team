"""
Trend Flow Analysis
"""

from typing import List, Dict
from collections import Counter
from src.topic_rec.state import TrendItem, TopicCluster


def analyze_cluster_flow(cluster: TopicCluster) -> str:
    if not cluster.items:
        return ""

    sorted_items = sorted(cluster.items, key=lambda x: x.trend_score, reverse=True)

    top_events = []
    for item in sorted_items[:3]:
        title_short = item.title[:50].strip()
        if len(item.title) > 50:
            title_short += "..."
        top_events.append(title_short)

    if len(top_events) >= 2:
        flow = " -> ".join(top_events)
    else:
        flow = top_events[0] if top_events else ""

    return flow


def enrich_clusters_with_flow(clusters: List[TopicCluster]) -> List[TopicCluster]:
    for cluster in clusters:
        cluster.trend_summary = analyze_cluster_flow(cluster)
    return clusters


def calculate_cluster_urgency(cluster: TopicCluster) -> str:
    community_count = cluster.source_distribution.get("reddit", 0) + \
                      cluster.source_distribution.get("hackernews", 0)

    total = cluster.item_count
    if total == 0:
        return "normal"

    community_ratio = community_count / total

    if community_ratio > 0.3 and cluster.avg_score > 0.05:
        return "urgent"
    elif community_ratio > 0.2 or cluster.avg_score > 0.1:
        return "normal"
    else:
        return "evergreen"


def get_trend_insights(clusters: List[TopicCluster]) -> Dict:
    if not clusters:
        return {}

    total_items = sum(c.item_count for c in clusters)

    top_topics = []
    for c in clusters[:5]:
        urgency = calculate_cluster_urgency(c)
        top_topics.append({
            "name": c.name,
            "count": c.item_count,
            "percentage": round(c.item_count / total_items * 100, 1) if total_items > 0 else 0,
            "avg_score": c.avg_score,
            "cluster_score": c.cluster_score,
            "urgency": urgency,
        })

    all_keywords = []
    for c in clusters:
        all_keywords.extend(c.keywords)

    hot_keywords = [kw for kw, _ in Counter(all_keywords).most_common(10)]

    return {
        "total_items": total_items,
        "cluster_count": len(clusters),
        "top_topics": top_topics,
        "hot_keywords": hot_keywords,
    }
