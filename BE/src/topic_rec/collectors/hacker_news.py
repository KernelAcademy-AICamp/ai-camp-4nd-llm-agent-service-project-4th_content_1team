import requests
import time
from datetime import datetime, timedelta, timezone
from src.topic_rec.state import TrendItem

HN_SEARCH_BY_DATE = "https://hn.algolia.com/api/v1/search_by_date"

def fetch_hn_trends(days=1, max_pages=2):
    cutoff_ts = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
    all_trends = []

    for page in range(max_pages):
        params = {"tags": "story", "hitsPerPage": 50, "page": page}
        try:
            r = requests.get(HN_SEARCH_BY_DATE, params=params, timeout=10)
            r.raise_for_status()
            hits = r.json().get("hits", [])

            if not hits: break

            for h in hits:
                if h.get("created_at_i", 0) < cutoff_ts: return all_trends

                all_trends.append(TrendItem(
                    source="hackernews",
                    original_id=str(h.get("objectID")),
                    title=h.get("title", ""),
                    content=h.get("story_text") or "",
                    link=h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                    engagement=(h.get("points") or 0) + (h.get("num_comments") or 0),
                    preset_category="Technology"
                ))
            time.sleep(0.3)
        except Exception as e:
            print(f"HackerNews collection error: {e}")
            break
    return all_trends
