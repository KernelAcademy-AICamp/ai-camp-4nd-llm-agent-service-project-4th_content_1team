from .google_trends import fetch_google_trends
from .google_news import fetch_google_news
from .youtube import fetch_youtube_trends
from .reddit import fetch_reddit_trends
from .hacker_news import fetch_hn_trends

__all__ = [
    "fetch_google_trends",
    "fetch_google_news",
    "fetch_youtube_trends",
    "fetch_reddit_trends",
    "fetch_hn_trends",
]
