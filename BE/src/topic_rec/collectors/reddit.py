import requests
import time
import random
from src.topic_rec.state import TrendItem

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
]

def fetch_reddit_trends(subreddits=None, max_posts=20):
    if subreddits is None:
        subreddits = ["popular", "worldnews", "technology", "entertainment", "finance"]
    all_trends = []
    for sub in subreddits:
        url = f"https://www.reddit.com/r/{sub}/hot.json"
        headers = {"User-Agent": random.choice(USER_AGENTS)}

        try:
            time.sleep(1)
            response = requests.get(url, headers=headers, params={"limit": 50}, timeout=10)
            if response.status_code != 200: continue

            posts = response.json().get("data", {}).get("children", [])
            category_map = {
                "technology": "Technology",
                "worldnews": "Society",
                "entertainment": "Entertainment",
                "finance": "Economy"
            }
            preset_cat = category_map.get(sub, None)

            for p in posts:
                data = p['data']
                if data.get("stickied"): continue

                all_trends.append(TrendItem(
                    source=f"reddit/r/{sub}",
                    original_id=data['id'],
                    title=data['title'],
                    content=data.get('selftext', '')[:300],
                    link=f"https://www.reddit.com{data.get('permalink', '')}",
                    engagement=data.get('score', 0),
                    preset_category=preset_cat
                ))
        except Exception as e:
            print(f"Reddit collection error (r/{sub}): {e}")

    return all_trends[:max_posts * len(subreddits)]
