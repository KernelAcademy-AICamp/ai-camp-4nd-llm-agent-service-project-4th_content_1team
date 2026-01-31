"""
Topic Clustering

계층 구조:
- CategoryCluster (대분류): Technology, Economy 등
- SubCategoryCluster (중분류): AI, Software, Hardware 등
- TrendTopic (소분류): 구체적인 트렌드 흐름 (GPT-5 출시, AI Agent 열풍 등)
"""

import math
from collections import Counter, defaultdict
from typing import List, Dict
from src.topic_rec.state import (
    TrendItem, TopicCluster,
    CategoryCluster, SubCategoryCluster, TrendTopic,
)


TOPIC_SEEDS = {
    "AI_Robot": [
        "AI", "robot", "GPT", "ChatGPT", "Claude", "Gemini", "LLM",
        "deep learning", "machine learning", "Optimus", "humanoid",
        "OpenAI", "Anthropic", "neural", "transformer"
    ],
    "BigTech_Strategy": [
        "Apple", "Google", "Microsoft", "Amazon", "Meta", "Tesla", "Nvidia",
        "Azure", "AWS", "GCP", "iPhone", "Galaxy", "MacBook"
    ],
    "Platform_Regulation": [
        "TikTok", "ban", "regulation",
        "privacy", "antitrust"
    ],
    "Crypto_Fintech": [
        "stablecoin", "crypto", "Bitcoin", "Ethereum",
        "blockchain"
    ],
    "Semiconductor_Hardware": [
        "semiconductor", "chip", "GPU", "CPU", "NPU",
        "TSMC", "Samsung", "SK Hynix", "Intel", "AMD", "Qualcomm",
        "memory", "HBM", "foundry", "EUV", "quantum"
    ],
    "Dev_OpenSource": [
        "GitHub", "Linux", "open source", "developer",
        "programming", "coding", "API", "SDK", "framework"
    ],
}


def find_matching_topics(item: TrendItem) -> List[str]:
    text = f"{item.title} {item.content}".lower()
    tags = [t.lower() for t in (item.ai_tags or [])]

    matched_topics = []

    for topic_name, keywords in TOPIC_SEEDS.items():
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in text or kw_lower in tags:
                matched_topics.append(topic_name)
                break

    return matched_topics


def cluster_trends(items: List[TrendItem]) -> List[TopicCluster]:
    topic_items: Dict[str, List[TrendItem]] = defaultdict(list)

    for item in items:
        matched = find_matching_topics(item)
        if matched:
            topic = matched[0]
            item.cluster_id = topic
            topic_items[topic].append(item)
        else:
            item.cluster_id = "Other"
            topic_items["Other"].append(item)

    clusters = []

    for topic_name, items_in_topic in topic_items.items():
        if not items_in_topic:
            continue

        all_keywords = []
        for item in items_in_topic:
            if item.ai_tags:
                all_keywords.extend(item.ai_tags)
        keyword_counts = Counter(all_keywords)
        top_keywords = [kw for kw, _ in keyword_counts.most_common(10)]

        source_dist = Counter(item.source.split('/')[0] for item in items_in_topic)

        total_engagement = sum(item.engagement for item in items_in_topic)
        avg_score = sum(item.trend_score for item in items_in_topic) / len(items_in_topic)

        volume_weight = math.log(len(items_in_topic) + 1, 10)
        cluster_score = round(volume_weight * avg_score, 4)

        cluster = TopicCluster(
            cluster_id=topic_name,
            name=topic_name.replace("_", "/"),
            keywords=top_keywords,
            items=items_in_topic,
            item_count=len(items_in_topic),
            total_engagement=total_engagement,
            avg_score=round(avg_score, 4),
            cluster_score=cluster_score,
            source_distribution=dict(source_dist),
        )

        clusters.append(cluster)

    clusters.sort(key=lambda c: c.cluster_score, reverse=True)

    for i, cluster in enumerate(clusters, 1):
        cluster.rank = i

    return clusters


def get_cluster_summary(clusters: List[TopicCluster], top_n: int = 5) -> str:
    lines = []

    for cluster in clusters[:top_n]:
        source_str = ", ".join(f"{k}:{v}" for k, v in cluster.source_distribution.items())
        kw_str = ", ".join(cluster.keywords[:5])

        lines.append(
            f"#{cluster.rank} {cluster.name}\n"
            f"   Count: {cluster.item_count} | Avg: {cluster.avg_score:.2f} | Score: {cluster.cluster_score:.3f}\n"
            f"   Keywords: {kw_str}\n"
            f"   Sources: {source_str}"
        )

    return "\n\n".join(lines)


# ============================================================
# 계층적 클러스터링 (Category → SubCategory → Topics)
# ============================================================

def cluster_by_hierarchy(items: List[TrendItem]) -> List[CategoryCluster]:
    """
    아이템들을 계층 구조로 클러스터링합니다.

    Category (대분류)
    └── SubCategory (중분류)
        └── TrendTopic (소분류) - 같은 주제의 아이템들
    """
    # Step 1: 카테고리별로 그룹화
    cat_items: Dict[str, List[TrendItem]] = defaultdict(list)
    for item in items:
        cat = item.ai_category or "Uncategorized"
        cat_items[cat].append(item)

    category_clusters = []

    for category, items_in_cat in cat_items.items():
        # Step 2: 서브카테고리별로 그룹화
        sub_items: Dict[str, List[TrendItem]] = defaultdict(list)
        for item in items_in_cat:
            sub = item.ai_sub_category or "General"
            sub_items[sub].append(item)

        sub_clusters = []

        for sub_category, items_in_sub in sub_items.items():
            # Step 3: 서브카테고리 내에서 토픽 클러스터링
            topics = _cluster_topics_within_subcategory(items_in_sub)

            # 서브카테고리 통계
            all_keywords = []
            for item in items_in_sub:
                if item.ai_tags:
                    all_keywords.extend(item.ai_tags)
            top_keywords = [kw for kw, _ in Counter(all_keywords).most_common(10)]

            source_dist = Counter(item.source.split('/')[0] for item in items_in_sub)
            avg_score = sum(item.trend_score for item in items_in_sub) / len(items_in_sub) if items_in_sub else 0
            volume_weight = math.log(len(items_in_sub) + 1, 10)

            sub_cluster = SubCategoryCluster(
                sub_category=sub_category,
                keywords=top_keywords,
                items=items_in_sub,
                topics=topics,
                item_count=len(items_in_sub),
                avg_score=round(avg_score, 4),
                cluster_score=round(volume_weight * avg_score, 4),
                source_distribution=dict(source_dist),
            )
            sub_clusters.append(sub_cluster)

        # 서브카테고리를 점수순으로 정렬
        sub_clusters.sort(key=lambda x: x.cluster_score, reverse=True)

        # 카테고리 통계
        cat_keywords = []
        for sub in sub_clusters:
            cat_keywords.extend(sub.keywords[:3])

        cat_cluster = CategoryCluster(
            category=category,
            sub_categories=sub_clusters,
            item_count=len(items_in_cat),
            avg_score=round(sum(item.trend_score for item in items_in_cat) / len(items_in_cat), 4) if items_in_cat else 0,
            top_keywords=[kw for kw, _ in Counter(cat_keywords).most_common(10)],
        )
        category_clusters.append(cat_cluster)

    # 카테고리를 아이템 수 기준으로 정렬
    category_clusters.sort(key=lambda x: x.item_count, reverse=True)

    return category_clusters


def _cluster_topics_within_subcategory(items: List[TrendItem]) -> List[TrendTopic]:
    """
    서브카테고리 내에서 유사한 아이템들을 토픽으로 묶습니다.
    현재는 TOPIC_SEEDS 기반의 규칙 매칭을 사용합니다.
    (추후 임베딩 기반 클러스터링으로 개선 가능)
    """
    topic_items: Dict[str, List[TrendItem]] = defaultdict(list)

    for item in items:
        matched = find_matching_topics(item)
        topic_name = matched[0] if matched else "Other"
        topic_items[topic_name].append(item)

    topics = []
    topic_id = 0

    for topic_name, items_in_topic in topic_items.items():
        if not items_in_topic:
            continue

        all_keywords = []
        for item in items_in_topic:
            if item.ai_tags:
                all_keywords.extend(item.ai_tags)
        top_keywords = [kw for kw, _ in Counter(all_keywords).most_common(5)]

        avg_score = sum(item.trend_score for item in items_in_topic) / len(items_in_topic)
        volume_weight = math.log(len(items_in_topic) + 1, 10)

        topic = TrendTopic(
            topic_id=f"topic_{topic_id}",
            name=topic_name.replace("_", "/"),
            keywords=top_keywords,
            items=items_in_topic,
            item_count=len(items_in_topic),
            avg_score=round(avg_score, 4),
            trend_score=round(volume_weight * avg_score, 4),
        )
        topics.append(topic)
        topic_id += 1

    # 토픽을 점수순으로 정렬
    topics.sort(key=lambda x: x.trend_score, reverse=True)

    return topics


def get_hierarchy_summary(category_clusters: List[CategoryCluster], top_n: int = 3) -> str:
    """계층 구조 요약 출력"""
    lines = []

    for cat in category_clusters[:top_n]:
        lines.append(f"[{cat.category}] {cat.item_count} items")

        for sub in cat.sub_categories[:3]:
            lines.append(f"  └── {sub.sub_category}: {sub.item_count} items (score: {sub.cluster_score:.3f})")

            for topic in sub.topics[:2]:
                lines.append(f"        └── {topic.name}: {topic.item_count} items")

    return "\n".join(lines)
