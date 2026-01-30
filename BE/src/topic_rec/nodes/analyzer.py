"""
Analyzer Node - Trend Insights Generation
"""

from src.topic_rec.state import TopicRecState
from src.topic_rec.utils import get_trend_insights


def analyze_node(state: TopicRecState) -> dict:
    """
    Generate trend insights from clusters.

    Outputs:
    - Total item count
    - Cluster count
    - Top topics with urgency
    - Hot keywords
    """
    print("[Analyzer] Generating insights...")

    clusters = state.get("clusters", [])

    if not clusters:
        print("[Analyzer] No clusters to analyze")
        return {
            "insights": {},
            "current_step": "analyze",
        }

    insights = get_trend_insights(clusters)

    print(f"[Analyzer] Insights generated:")
    print(f"    Total items: {insights.get('total_items', 0)}")
    print(f"    Clusters: {insights.get('cluster_count', 0)}")
    print(f"    Hot keywords: {', '.join(insights.get('hot_keywords', [])[:5])}")

    return {
        "insights": insights,
        "current_step": "analyze",
    }
