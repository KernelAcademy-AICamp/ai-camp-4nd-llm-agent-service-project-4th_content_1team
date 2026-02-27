"""
Collector Node - Data Collection from multiple sources

Source Selector Agent의 결과(source_config)를 기반으로
Core/Adjacent 2-Layer로 트렌드를 수집합니다.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from src.topic_rec.state import TopicRecState
from src.topic_rec.collectors import (
    fetch_reddit_trends,
    fetch_reddit_search,
    fetch_hn_trends,
    fetch_google_news,
    fetch_google_trends,
)


def _tag_source_layer(trends: list, layer: str) -> list:
    """수집된 TrendItem에 source_layer 태그를 추가합니다."""
    for item in trends:
        item.source_layer = layer
    return trends


def _collect_reddit(core_reddit: dict, adj_reddit: dict) -> list:
    """
    Reddit 수집 (서브레딧 + 키워드 검색 병행).
    Core/Adjacent 각각 서브레딧 인기글 + 키워드 검색 결과를 합칩니다.
    """
    all_reddit = []
    seen_ids = set()

    def _add_unique(trends, layer):
        tagged = _tag_source_layer(trends, layer)
        added = 0
        for t in tagged:
            if t.original_id not in seen_ids:
                seen_ids.add(t.original_id)
                all_reddit.append(t)
                added += 1
        return added

    for layer, cfg in [("core", core_reddit), ("adjacent", adj_reddit)]:
        # 서브레딧 수집
        subs = cfg.get("subreddits", []) if isinstance(cfg, dict) else cfg
        if subs:
            try:
                trends = fetch_reddit_trends(subreddits=subs)
                count = _add_unique(trends, layer)
                print(f"     {layer.title()} Reddit subs: {count} items from {subs}")
            except Exception as e:
                print(f"     {layer.title()} Reddit subs error: {e}")

        # 키워드 검색
        keywords = cfg.get("keywords", []) if isinstance(cfg, dict) else []
        if keywords:
            try:
                trends = fetch_reddit_search(keywords=keywords)
                count = _add_unique(trends, layer)
                print(f"     {layer.title()} Reddit search: {count} items (keywords: {keywords})")
            except Exception as e:
                print(f"     {layer.title()} Reddit search error: {e}")

    return all_reddit


def _collect_google_news(core_cats: list, adj_cats: list) -> list:
    """Google News 수집 (Core + Adjacent)."""
    all_news = []

    if core_cats:
        try:
            core_trends = fetch_google_news(categories=core_cats)
            _tag_source_layer(core_trends, "core")
            all_news.extend(core_trends)
            print(f"     Core News: {len(core_trends)} items from {core_cats}")
        except Exception as e:
            print(f"     Core News error: {e}")

    if adj_cats:
        try:
            adj_trends = fetch_google_news(categories=adj_cats)
            _tag_source_layer(adj_trends, "adjacent")
            all_news.extend(adj_trends)
            print(f"     Adjacent News: {len(adj_trends)} items from {adj_cats}")
        except Exception as e:
            print(f"     Adjacent News error: {e}")

    return all_news


def _collect_hacker_news(core_hn: dict, adj_hn: dict) -> list:
    """Hacker News 수집 (Core + Adjacent)."""
    all_hn = []

    if core_hn.get("use", False):
        try:
            keywords = core_hn.get("keywords", [])
            core_trends = fetch_hn_trends(days=1, keywords=keywords)
            _tag_source_layer(core_trends, "core")
            all_hn.extend(core_trends)
            print(f"     Core HN: {len(core_trends)} items (keywords: {keywords})")
        except Exception as e:
            print(f"     Core HN error: {e}")

    if adj_hn.get("use", False):
        try:
            keywords = adj_hn.get("keywords", [])
            adj_trends = fetch_hn_trends(days=1, keywords=keywords)
            _tag_source_layer(adj_trends, "adjacent")
            all_hn.extend(adj_trends)
            print(f"     Adjacent HN: {len(adj_trends)} items (keywords: {keywords})")
        except Exception as e:
            print(f"     Adjacent HN error: {e}")

    return all_hn


def _collect_google_trends(core_keywords: list, adj_keywords: list) -> list:
    """Google Trends 수집 (전체 KR, 태그만 구분)."""
    all_gt = []

    try:
        gt_trends = fetch_google_trends("KR")
        # Google Trends는 전체 수집 후 core로 태그 (키워드 필터링은 클러스터링에서)
        _tag_source_layer(gt_trends, "core")
        all_gt.extend(gt_trends)
        print(f"     Google Trends: {len(gt_trends)} items")
    except Exception as e:
        print(f"     Google Trends error: {e}")

    return all_gt


def collect_node(state: TopicRecState) -> dict:
    """
    Collect trends from multiple sources.

    source_config가 있으면 동적 수집 (Core/Adjacent 분리),
    없으면 기존 하드코딩 방식으로 fallback.
    """
    print("[Collector] Starting data collection...")

    source_config = state.get("source_config")

    # source_config 없으면 기존 방식 fallback
    if not source_config:
        print("[Collector] No source_config, using default sources")
        source_config = {
            "core": {
                "reddit": {"subreddits": [], "keywords": []},
                "google_news": ["TECHNOLOGY", "BUSINESS", "SCIENCE"],
                "hacker_news": {"use": True, "keywords": []},
                "google_trends": [],
            },
            "adjacent": {
                "reddit": {"subreddits": ["technology", "Futurology", "programming"], "keywords": []},
                "google_news": [],
                "hacker_news": {"use": False, "keywords": []},
                "google_trends": [],
            },
        }

    core = source_config.get("core", {})
    adjacent = source_config.get("adjacent", {})

    all_trends = []

    # Reddit: 순차 처리 (rate limit 방지)
    # Google News, Hacker News, Google Trends: 병렬 처리
    print("  -> Reddit (sequential)...")
    reddit_trends = _collect_reddit(
        core.get("reddit", {}),
        adjacent.get("reddit", {}),
    )

    # 나머지 3개 소스는 병렬
    print("  -> Google News + Hacker News + Google Trends (parallel)...")
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(
                _collect_google_news,
                core.get("google_news", []),
                adjacent.get("google_news", []),
            ): "google_news",
            executor.submit(
                _collect_hacker_news,
                core.get("hacker_news", {"use": False, "keywords": []}),
                adjacent.get("hacker_news", {"use": False, "keywords": []}),
            ): "hacker_news",
            executor.submit(
                _collect_google_trends,
                core.get("google_trends", []),
                adjacent.get("google_trends", []),
            ): "google_trends",
        }

        for future in as_completed(futures):
            source_name = futures[future]
            try:
                result = future.result()
                all_trends.extend(result)
            except Exception as e:
                print(f"     {source_name} error: {e}")

    all_trends.extend(reddit_trends)

    print(f"[Collector] Total: {len(all_trends)} items collected")

    core_count = sum(1 for t in all_trends if getattr(t, "source_layer", None) == "core")
    adj_count = sum(1 for t in all_trends if getattr(t, "source_layer", None) == "adjacent")
    print(f"[Collector] Core: {core_count} / Adjacent: {adj_count}")

    return {
        "trends": all_trends,
        "current_step": "collect",
    }
