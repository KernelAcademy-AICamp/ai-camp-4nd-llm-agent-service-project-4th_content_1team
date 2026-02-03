import requests
from src.topic_rec.state import TrendItem

def fetch_youtube_trends(api_key, region_code="KR"):
    if api_key == "YOUR_API_KEY":
        print("YouTube API Key not configured.")
        return []

    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": 10,
        "key": api_key
    }

    all_trends = []
    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            all_trends.append(TrendItem(
                source=f"youtube/{region_code}",
                original_id=item.get("id"),
                title=snippet.get("title"),
                content=snippet.get("description", "")[:200],
                link=f"https://www.youtube.com/watch?v={item.get('id')}",
                engagement=int(stats.get("viewCount", 0))
            ))
    except Exception as e:
        print(f"YouTube collection error: {e}")
    return all_trends
