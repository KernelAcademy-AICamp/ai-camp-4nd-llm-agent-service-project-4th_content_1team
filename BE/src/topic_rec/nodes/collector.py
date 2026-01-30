"""
Collector Node - Data Collection from multiple sources
"""

import os
from src.topic_rec.state import TopicRecState
from src.topic_rec.collectors import (
    fetch_reddit_trends,
    fetch_hn_trends,
    fetch_google_news,
    fetch_google_trends,
    fetch_youtube_trends,
)


def collect_node(state: TopicRecState) -> dict:
    """
    Collect trends from multiple sources.

    Sources:
    - Reddit (r/popular, r/technology, etc.)
    - Hacker News
    - Google News
    - Google Trends
    - YouTube (if API key provided)
    """
    print("[Collector] Starting data collection...")

    all_trends = []

    # Reddit
    print("  -> Reddit...")
    try:
        reddit_trends = fetch_reddit_trends()
        all_trends.extend(reddit_trends)
        print(f"     Collected {len(reddit_trends)} items")
    except Exception as e:
        print(f"     Error: {e}")

    # Hacker News
    print("  -> Hacker News...")
    try:
        hn_trends = fetch_hn_trends(days=1)
        all_trends.extend(hn_trends)
        print(f"     Collected {len(hn_trends)} items")
    except Exception as e:
        print(f"     Error: {e}")

    # Google News
    print("  -> Google News...")
    try:
        news_trends = fetch_google_news()
        all_trends.extend(news_trends)
        print(f"     Collected {len(news_trends)} items")
    except Exception as e:
        print(f"     Error: {e}")

    # Google Trends
    print("  -> Google Trends...")
    try:
        gt_trends = fetch_google_trends("KR")
        all_trends.extend(gt_trends)
        print(f"     Collected {len(gt_trends)} items")
    except Exception as e:
        print(f"     Error: {e}")

    # YouTube (optional)
    yt_api_key = os.getenv("YOUTUBE_API_KEY")
    if yt_api_key and yt_api_key != "YOUR_API_KEY":
        print("  -> YouTube...")
        try:
            yt_trends = fetch_youtube_trends(yt_api_key)
            all_trends.extend(yt_trends)
            print(f"     Collected {len(yt_trends)} items")
        except Exception as e:
            print(f"     Error: {e}")

    print(f"[Collector] Total: {len(all_trends)} items collected")

    return {
        "trends": all_trends,
        "current_step": "collect",
    }
