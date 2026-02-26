"""
Clusterer Node - 키워드 기반 자동 그룹핑

키워드 동시 등장(co-occurrence) 기반으로 비슷한 트렌드끼리 자동 그룹핑하고,
각 그룹의 요약(제목 5개 + 본문 1개)을 생성하여 Recommender에 전달합니다.
"""

from src.topic_rec.state import TopicRecState
from src.topic_rec.utils.topic_clustering import cluster_by_keywords, build_group_summary


def cluster_node(state: TopicRecState) -> dict:
    """
    Cluster processed trends by keyword co-occurrence.
    """
    print("[Clusterer] Starting keyword-based clustering...")

    trends = state.get("processed_trends", [])

    if not trends:
        print("[Clusterer] No trends to cluster")
        return {
            "clusters": [],
            "category_clusters": [],
            "current_step": "cluster",
            "error": "No processed trends",
        }

    # 키워드 기반 자동 그룹핑
    clusters = cluster_by_keywords(trends)

    # 그룹별 요약 생성 (Recommender LLM 전달용)
    for cluster in clusters:
        cluster.trend_summary = build_group_summary(cluster)

    print(f"[Clusterer] Created {len(clusters)} groups")
    for c in clusters[:5]:
        core = sum(1 for i in c.items if getattr(i, "source_layer", None) == "core")
        adj = sum(1 for i in c.items if getattr(i, "source_layer", None) == "adjacent")
        print(f"  #{c.rank} {c.name} ({c.item_count}건, score:{c.cluster_score:.3f}, core:{core}/adj:{adj})")

    return {
        "clusters": clusters,
        "category_clusters": [],
        "current_step": "cluster",
    }
