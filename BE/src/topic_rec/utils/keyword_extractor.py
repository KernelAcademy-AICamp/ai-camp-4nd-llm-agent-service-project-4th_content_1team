"""
Keyword Extractor (No LLM)
"""

import re
from collections import Counter
from typing import List
from src.topic_rec.state import TrendItem

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "need",
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
    "into", "through", "during", "before", "after", "above", "below",
    "between", "under", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "each",
    "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "just",
    "and", "but", "if", "or", "because", "until", "while",
    "this", "that", "these", "those", "what", "which", "who", "whom",
    "new", "news", "says", "said", "report", "reports", "reported",
    "according", "sources", "source", "officials", "official",
    "year", "years", "month", "months", "week", "weeks", "day", "days",
    "time", "times", "people", "person", "man", "woman", "thing", "things",
    "way", "ways", "world", "today", "now", "just", "like", "get", "got",
    "make", "made", "take", "took", "come", "came", "see", "saw",
    "know", "think", "want", "use", "used", "find", "found",
    "first", "last", "next", "back", "still", "also", "even", "well",
    "really", "actually", "probably", "maybe", "seems", "looks",
    "going", "getting", "being", "having", "doing", "making",
    "one", "two", "three", "many", "much", "some", "any", "every",
    "show", "hn", "ask", "tell", "showhn", "askhn",
    "til", "iama", "ama", "eli5", "dae", "imho", "imo",
    "reddit", "subreddit", "post", "posts", "comment", "comments",
    "good", "bad", "best", "worst", "better", "worse",
    "big", "small", "large", "little", "great", "long", "short",
    "high", "low", "old", "young", "early", "late",
    "right", "wrong", "true", "false", "real", "fake",
    "free", "open", "full", "empty", "easy", "hard", "simple",
}

PRIORITY_PATTERNS = [
    r"\b(Apple|Google|Microsoft|Amazon|Meta|Tesla|Nvidia|OpenAI|Samsung)\b",
    r"\b(Netflix|Disney|Sony|Intel|AMD|Qualcomm|IBM|Oracle|TikTok)\b",
    r"\b(iPhone|iPad|MacBook|Android|Windows|Linux|ChatGPT|GPT-\d|Claude|Gemini)\b",
    r"\b(Galaxy|Pixel|Surface|PlayStation|Xbox|Switch)\b",
    r"\b(AI|API|GPU|CPU|VR|AR|IoT|5G|6G|LLM|ML)\b",
    r"\b(Bitcoin|Ethereum|BTC|ETH|crypto)\b",
    r"\b(Azure|AWS|GCP|GitHub|Docker|Kubernetes)\b",
]


def extract_keywords(text: str, top_n: int = 5) -> List[str]:
    keywords = []

    for pattern in PRIORITY_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        keywords.extend(matches)

    proper_nouns = re.findall(r"\b[A-Z][a-z]{2,}\b", text)
    korean = re.findall(r"[가-힣]{2,}", text)

    all_words = keywords + proper_nouns + korean

    filtered = [
        w for w in all_words
        if w.lower() not in STOPWORDS and w not in STOPWORDS and len(w) >= 2
    ]

    counts = Counter(filtered)
    return [word for word, _ in counts.most_common(top_n)]


def extract_tech_keywords(text: str, top_n: int = 5) -> List[str]:
    tech_patterns = [
        r"\b(Apple|Google|Microsoft|Amazon|Meta|Tesla|Nvidia|OpenAI|Samsung|Intel|AMD|TikTok)\b",
        r"\b(iPhone|iPad|MacBook|Android|iOS|Windows|Linux|ChatGPT|Gemini|Claude)\b",
        r"\b(AI|API|GPU|CPU|SSD|RAM|5G|WiFi|Bluetooth|USB-C|LLM)\b",
        r"\b(GitHub|Docker|Kubernetes|AWS|Azure|GCP)\b",
    ]

    keywords = []
    for pattern in tech_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        keywords.extend(matches)

    counts = Counter(keywords)
    return [word for word, _ in counts.most_common(top_n)]


def enrich_with_keywords(items: List[TrendItem], top_n: int = 5) -> List[TrendItem]:
    for item in items:
        text = f"{item.title} {item.content}"

        if item.ai_category == "Technology":
            tech_kw = extract_tech_keywords(text, top_n=3)
            general_kw = extract_keywords(text, top_n=top_n)
            all_kw = tech_kw + [kw for kw in general_kw if kw not in tech_kw]
            item.ai_tags = all_kw[:top_n] if all_kw else []
        else:
            item.ai_tags = extract_keywords(text, top_n=top_n)

    return items


def get_top_keywords_by_category(items: List[TrendItem], top_n: int = 10) -> dict:
    category_keywords = {}

    for item in items:
        cat = item.ai_category or "Uncategorized"
        if cat not in category_keywords:
            category_keywords[cat] = []

        if item.ai_tags:
            category_keywords[cat].extend(item.ai_tags)

    result = {}
    for cat, keywords in category_keywords.items():
        counts = Counter(keywords)
        result[cat] = [kw for kw, _ in counts.most_common(top_n)]

    return result
