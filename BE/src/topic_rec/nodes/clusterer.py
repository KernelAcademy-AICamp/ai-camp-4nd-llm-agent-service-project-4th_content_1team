"""
Clusterer Node - Topic Clustering

계층 구조 클러스터링:
- CategoryCluster (대분류): Technology, Economy 등
- SubCategoryCluster (중분류): AI, Software 등
- TrendTopic (소분류): 구체적인 트렌드 흐름
"""

from src.topic_rec.state import TopicRecState
from src.topic_rec.utils import (
    cluster_trends,
    cluster_by_hierarchy,
    enrich_clusters_with_flow,
    get_hierarchy_summary,
)


def cluster_node(state: TopicRecState) -> dict:
    """
    Cluster processed trends into topics.

    계층 구조:
    1. Category별로 그룹화 (대분류)
    2. SubCategory별로 그룹화 (중분류)
    3. 토픽별로 클러스터링 (소분류)
    """
    print("[Clusterer] Starting hierarchical clustering...")

    trends = state.get("processed_trends", [])

    if not trends:
        print("[Clusterer] No trends to cluster")
        return {
            "clusters": [],
            "category_clusters": [],
            "current_step": "cluster",
            "error": "No processed trends",
        }

    # Step 1: 계층적 클러스터링 (새로운 방식)
    print("  -> Building category hierarchy...")
    category_clusters = cluster_by_hierarchy(trends)

    # 계층 구조 로그
    print(f"[Clusterer] Created {len(category_clusters)} category clusters")
    print(get_hierarchy_summary(category_clusters, top_n=2))

    # Step 2: 기존 클러스터링 (호환성 유지)
    print("  -> Creating legacy clusters...")
    clusters = cluster_trends(trends)
    clusters = enrich_clusters_with_flow(clusters)

    print(f"[Clusterer] Legacy clusters: {len(clusters)}")

    return {
        "category_clusters": category_clusters,
        "clusters": clusters,
        "current_step": "cluster",
    }
