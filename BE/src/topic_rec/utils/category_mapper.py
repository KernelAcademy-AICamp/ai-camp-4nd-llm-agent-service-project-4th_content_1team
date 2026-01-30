"""
Rule-based Category Mapping (No LLM)

계층 구조:
- Category (대분류): Technology, Economy, Entertainment, Sports, Society
- SubCategory (중분류): AI, SW, Hardware, Finance, Investment 등
"""

from typing import List
from src.topic_rec.state import TrendItem

CATEGORY_NORMALIZE_MAP = {
    "technology": "Technology",
    "tech": "Technology",
    "science": "Technology",
    "business": "Economy",
    "economy": "Economy",
    "finance": "Economy",
    "entertainment": "Entertainment",
    "sports": "Sports",
    "society": "Society",
    "politics": "Society",
    "lifestyle": "Lifestyle",
    "culture": "Culture",
}

# 서브카테고리 매핑 (중분류)
SUBCATEGORY_KEYWORDS = {
    "Technology": {
        "AI": [
            "AI", "artificial intelligence", "ChatGPT", "GPT", "Claude", "Gemini",
            "LLM", "machine learning", "deep learning", "neural network",
            "OpenAI", "Anthropic", "transformer", "agent", "copilot",
        ],
        "Software": [
            "software", "app", "application", "programming", "coding", "developer",
            "GitHub", "open source", "API", "SDK", "framework", "library",
            "Python", "JavaScript", "Rust", "Go", "Java", "Linux",
        ],
        "Hardware": [
            "semiconductor", "chip", "GPU", "CPU", "NPU", "memory", "HBM",
            "TSMC", "Intel", "AMD", "Qualcomm", "Samsung Foundry",
            "iPhone", "Galaxy", "MacBook", "laptop", "PC", "smartphone",
        ],
        "Cloud": [
            "cloud", "AWS", "Azure", "GCP", "server", "infrastructure",
            "kubernetes", "docker", "microservice", "serverless",
        ],
        "Security": [
            "security", "cyber", "hack", "vulnerability", "privacy",
            "encryption", "firewall", "malware", "ransomware",
        ],
    },
    "Economy": {
        "Finance": [
            "stock", "market", "trading", "Fed", "interest rate",
            "inflation", "GDP", "bond", "treasury", "forex",
        ],
        "Investment": [
            "investment", "investor", "portfolio", "fund", "ETF",
            "Warren Buffett", "venture capital", "angel",
        ],
        "Crypto": [
            "crypto", "bitcoin", "ethereum", "blockchain", "stablecoin",
            "NFT", "DeFi", "web3", "token",
        ],
        "Business": [
            "startup", "IPO", "acquisition", "merger", "earnings",
            "revenue", "profit", "CEO", "unicorn",
        ],
    },
    "Entertainment": {
        "Movies": [
            "movie", "film", "cinema", "Netflix", "Disney", "HBO",
            "Marvel", "DC", "Oscar", "box office",
        ],
        "Music": [
            "music", "album", "concert", "tour", "Grammy", "Billboard",
            "Spotify", "K-pop", "BTS", "singer", "artist",
        ],
        "Gaming": [
            "game", "gaming", "PlayStation", "Xbox", "Nintendo", "Steam",
            "esports", "streamer", "Twitch",
        ],
    },
    "Sports": {
        "Football": ["NFL", "football", "Super Bowl", "touchdown"],
        "Basketball": ["NBA", "basketball", "Lakers", "Warriors"],
        "Soccer": ["FIFA", "UEFA", "Premier League", "World Cup", "soccer"],
        "Baseball": ["MLB", "baseball", "World Series"],
    },
    "Society": {
        "Politics": [
            "election", "president", "congress", "senate", "parliament",
            "Trump", "Biden", "Democrat", "Republican", "vote",
        ],
        "World": [
            "Ukraine", "Russia", "China", "military", "war", "conflict",
            "NATO", "UN", "diplomacy",
        ],
        "Legal": [
            "court", "lawsuit", "verdict", "supreme court", "regulation",
            "antitrust", "ban", "fine",
        ],
    },
}

def normalize_category(cat: str) -> str:
    if not cat:
        return "Uncategorized"
    return CATEGORY_NORMALIZE_MAP.get(cat.lower(), cat.title())


TRUSTED_SOURCES = {
    "hackernews": "Technology",
    "reddit/r/technology": "Technology",
    "reddit/r/programming": "Technology",
    "reddit/r/machinelearning": "Technology",
    "reddit/r/artificial": "Technology",
    "reddit/r/finance": "Economy",
    "reddit/r/investing": "Economy",
    "reddit/r/worldnews": "Society",
    "reddit/r/news": "Society",
    "reddit/r/entertainment": "Entertainment",
    "reddit/r/movies": "Entertainment",
    "reddit/r/music": "Entertainment",
    "reddit/r/sports": "Sports",
    "google_news/TECHNOLOGY": "Technology",
    "google_news/SCIENCE": "Technology",
    "google_news/BUSINESS": "Economy",
    "google_news/ENTERTAINMENT": "Entertainment",
    "google_news/SPORTS": "Sports",
    "youtube/KR": None,
}

UNTRUSTED_SOURCES = [
    "reddit/r/popular",
    "reddit/r/all",
    "google_trends",
]

KEYWORD_CATEGORY_MAP = {
    "Technology": [
        "Apple", "Google", "Microsoft", "Samsung", "Nvidia", "Tesla", "OpenAI",
        "iPhone", "Android", "MacBook", "iPad", "Galaxy", "Pixel",
        "ChatGPT", "GPT-4", "GPT-5", "Gemini", "Claude", "Copilot",
        "AI", "API", "GPU", "CPU", "SSD", "RAM", "5G", "6G", "WiFi",
        "blockchain", "crypto", "bitcoin", "ethereum",
        "software", "hardware", "firmware", "algorithm",
        "machine learning", "deep learning", "neural network",
        "startup", "silicon valley", "venture capital",
    ],
    "Economy": [
        "stock", "market", "investment", "investor", "trading", "trader",
        "Fed", "inflation", "recession", "GDP", "interest rate",
        "earnings", "revenue", "profit", "IPO", "acquisition", "merger",
    ],
    "Entertainment": [
        "movie", "film", "drama", "series", "Netflix", "Disney", "HBO",
        "Marvel", "DC", "Star Wars", "anime",
        "music", "album", "concert", "tour", "Grammy", "Billboard",
        "celebrity", "actor", "actress", "singer", "idol", "BTS", "K-pop",
    ],
    "Sports": [
        "NBA", "NFL", "MLB", "NHL", "FIFA", "UEFA", "Premier League",
        "soccer", "football", "basketball", "baseball", "tennis", "golf",
        "Olympic", "World Cup", "championship", "playoff",
    ],
    "Society": [
        "election", "president", "congress", "senate", "parliament",
        "Trump", "Biden", "Democrat", "Republican",
        "war", "Ukraine", "Russia", "China", "military",
        "immigration", "border", "refugee",
        "court", "lawsuit", "verdict", "supreme court",
    ],
}


def map_categories(items: List[TrendItem]) -> List[TrendItem]:
    for item in items:
        if item.preset_category:
            item.ai_category = normalize_category(item.preset_category)
            continue

        if item.source in TRUSTED_SOURCES:
            category = TRUSTED_SOURCES[item.source]
            if category:
                item.ai_category = category
                continue

        is_untrusted = any(
            item.source.startswith(src) for src in UNTRUSTED_SOURCES
        )
        if is_untrusted:
            item.ai_category = "Uncategorized"
            continue

        text = f"{item.title} {item.content}"
        matched = False

        for cat, keywords in KEYWORD_CATEGORY_MAP.items():
            for kw in keywords:
                if kw.lower() in text.lower():
                    item.ai_category = cat
                    matched = True
                    break
            if matched:
                break

        if not matched:
            item.ai_category = "Uncategorized"

    return items


def get_category_stats(items: List[TrendItem]) -> dict:
    stats = {}
    for item in items:
        cat = item.ai_category or "Uncategorized"
        stats[cat] = stats.get(cat, 0) + 1
    return dict(sorted(stats.items(), key=lambda x: x[1], reverse=True))


def filter_by_categories(items: List[TrendItem], categories: List[str]) -> List[TrendItem]:
    return [item for item in items if item.ai_category in categories]


def map_subcategory(item: TrendItem) -> str:
    """
    아이템의 서브카테고리를 결정합니다.
    카테고리가 먼저 결정되어 있어야 합니다.
    """
    category = item.ai_category
    if not category or category not in SUBCATEGORY_KEYWORDS:
        return "General"

    text = f"{item.title} {item.content}".lower()
    subcategory_map = SUBCATEGORY_KEYWORDS[category]

    for sub_cat, keywords in subcategory_map.items():
        for kw in keywords:
            if kw.lower() in text:
                return sub_cat

    return "General"


def map_subcategories(items: List[TrendItem]) -> List[TrendItem]:
    """
    모든 아이템에 서브카테고리를 매핑합니다.
    """
    for item in items:
        item.ai_sub_category = map_subcategory(item)
    return items


def get_subcategory_stats(items: List[TrendItem]) -> dict:
    """카테고리별 서브카테고리 통계"""
    stats = {}
    for item in items:
        cat = item.ai_category or "Uncategorized"
        sub = item.ai_sub_category or "General"
        key = f"{cat}/{sub}"
        stats[key] = stats.get(key, 0) + 1
    return dict(sorted(stats.items(), key=lambda x: x[1], reverse=True))
