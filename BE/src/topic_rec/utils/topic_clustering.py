"""
Topic Clustering - 키워드 기반 자동 그룹핑

키워드 동시 등장(co-occurrence) 기반으로 비슷한 트렌드끼리 자동 그룹핑.
하드코딩 TOPIC_SEEDS 없이, 데이터에서 자연스럽게 그룹이 만들어짐.
"""

import math
from collections import Counter, defaultdict
from typing import List

from src.topic_rec.state import TrendItem, TopicCluster


def cluster_by_keywords(items: List[TrendItem]) -> List[TopicCluster]:
    """
    키워드 동시 등장(co-occurrence) 기반 자동 그룹핑.

    1. ai_tags에서 키워드 빈도 계산
    2. 너무 흔한 키워드(40% 이상 문서에 등장) 제외하여 chaining 방지
    3. Union-Find로 키워드 1개 이상 겹치는 아이템끼리 그룹핑
    4. 2개 미만 그룹은 "기타"로 병합
    """
    n = len(items)
    if n == 0:
        return []

    # Step 1: 키워드 빈도 계산
    kw_freq = Counter()
    for item in items:
        for tag in (item.ai_tags or []):
            kw_freq[tag.lower()] += 1

    # Step 2: 너무 흔한 키워드 제외 (그룹핑용에서만, 결과 표시에는 유지)
    max_freq = max(n * 0.3, 3)
    common_keywords = {kw for kw, freq in kw_freq.items() if freq > max_freq}

    grouping_tags = []
    for item in items:
        tags = {t.lower() for t in (item.ai_tags or [])} - common_keywords
        grouping_tags.append(tags)

    # Step 3: Union-Find
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for i in range(n):
        if not grouping_tags[i]:
            continue
        for j in range(i + 1, n):
            if not grouping_tags[j]:
                continue
            if len(grouping_tags[i] & grouping_tags[j]) >= 2:
                union(i, j)

    # Step 4: 그룹 수집
    raw_groups = defaultdict(list)
    for i in range(n):
        raw_groups[find(i)].append(i)

    # Step 5: TopicCluster 변환
    clusters = []
    misc_items = []

    for group_indices in raw_groups.values():
        group_items = [items[i] for i in group_indices]

        if len(group_items) < 2:
            misc_items.extend(group_items)
            continue

        # 그룹 내 키워드 빈도 (원본 ai_tags 사용)
        keyword_counter = Counter()
        for item in group_items:
            for tag in (item.ai_tags or []):
                keyword_counter[tag] += 1
        top_keywords = [kw for kw, _ in keyword_counter.most_common(10)]

        name = " / ".join(top_keywords[:3]) if top_keywords else "Unknown"

        total_engagement = sum(item.engagement for item in group_items)
        avg_score = sum(item.trend_score for item in group_items) / len(group_items)
        volume_weight = math.log(len(group_items) + 1, 10)
        cluster_score = round(volume_weight * avg_score, 4)
        source_dist = Counter(item.source.split('/')[0] for item in group_items)

        clusters.append(TopicCluster(
            cluster_id=f"group_{len(clusters)}",
            name=name,
            keywords=top_keywords,
            items=group_items,
            item_count=len(group_items),
            total_engagement=total_engagement,
            avg_score=round(avg_score, 4),
            cluster_score=cluster_score,
            source_distribution=dict(source_dist),
        ))

    # 기타 그룹
    if misc_items:
        misc_kw = Counter()
        for item in misc_items:
            for tag in (item.ai_tags or []):
                misc_kw[tag] += 1

        misc_engagement = sum(item.engagement for item in misc_items)
        misc_avg = sum(item.trend_score for item in misc_items) / len(misc_items)

        clusters.append(TopicCluster(
            cluster_id="group_misc",
            name="기타",
            keywords=[kw for kw, _ in misc_kw.most_common(5)],
            items=misc_items,
            item_count=len(misc_items),
            total_engagement=misc_engagement,
            avg_score=round(misc_avg, 4),
            cluster_score=0,
            source_distribution=dict(Counter(
                item.source.split('/')[0] for item in misc_items
            )),
        ))

    # 점수순 정렬 + 랭킹
    clusters.sort(key=lambda c: c.cluster_score, reverse=True)
    for i, c in enumerate(clusters, 1):
        c.rank = i

    return clusters


def build_group_summary(cluster: TopicCluster, max_titles: int = 5) -> str:
    """
    그룹 요약 생성 (Recommender LLM 전달용).

    - 주요 제목 최대 5개 (점수순)
    - 대표 본문 1개 (내용이 있는 것 중 점수 최고)
    - core/adjacent 분포
    """
    sorted_items = sorted(cluster.items, key=lambda x: x.trend_score, reverse=True)

    # 주요 제목
    titles = []
    for item in sorted_items[:max_titles]:
        titles.append(f'    - "{item.title}" ({item.trend_score:.2f})')

    # 대표 본문 (내용이 있는 것 중 점수 최고)
    content_item = None
    for item in sorted_items:
        if item.content and len(item.content.strip()) > 20:
            content_item = item
            break

    # core/adjacent 분포
    core_count = sum(
        1 for item in cluster.items
        if getattr(item, "source_layer", None) == "core"
    )
    adj_count = sum(
        1 for item in cluster.items
        if getattr(item, "source_layer", None) == "adjacent"
    )
    layer_str = f"core {core_count} / adjacent {adj_count}"

    lines = [
        f"[{cluster.name}] ({cluster.item_count}건, 평균점수 {cluster.avg_score:.2f}, {layer_str})",
        f"  키워드: {', '.join(cluster.keywords[:5])}",
        f"  주요 제목:",
    ]
    lines.extend(titles)

    if content_item:
        preview = content_item.content.strip()[:300]
        lines.append(f"  대표 본문:")
        lines.append(f'    "{preview}"')

    return "\n".join(lines)
