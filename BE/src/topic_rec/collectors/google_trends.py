import requests
import xml.etree.ElementTree as ET
from src.topic_rec.state import TrendItem

def fetch_google_trends(region="KR"):
    url = f"https://trends.google.com/trending/rss?geo={region.upper()}"
    ns = {'ht': 'http://trends.google.com/trends/trendingsearches/daily'}
    all_trends = []

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        root = ET.fromstring(res.content)

        for item in root.findall(".//item"):
            title = item.find("title").text
            traffic = item.find("ht:approx_traffic", ns)
            traffic_val = int(traffic.text.replace(",","").replace("+","")) if traffic is not None else 0

            all_trends.append(TrendItem(
                source=f"google_trends/{region}",
                original_id=f"gt-{region}-{title}",
                title=title,
                content=item.find("description").text or "",
                link=item.find("link").text,
                engagement=traffic_val
            ))
    except Exception as e:
        print(f"Google Trends collection error: {e}")
    return all_trends
