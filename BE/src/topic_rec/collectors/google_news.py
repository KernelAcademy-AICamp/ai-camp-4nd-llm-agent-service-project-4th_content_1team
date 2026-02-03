import requests
import xml.etree.ElementTree as ET
from src.topic_rec.state import TrendItem

def fetch_google_news(categories=None):
    if categories is None:
        categories = ["TECHNOLOGY", "BUSINESS", "SCIENCE", "ENTERTAINMENT", "SPORTS"]

    all_trends = []

    if isinstance(categories, str):
        categories = [categories]

    for category in categories:
        url = f"https://news.google.com/rss/headlines/section/topic/{category}?hl=ko&gl=KR&ceid=KR:ko"

        try:
            res = requests.get(url, timeout=10)
            if res.status_code != 200:
                continue

            root = ET.fromstring(res.content)
            count = 0
            for item in root.findall(".//item"):
                link = item.find("link").text
                all_trends.append(TrendItem(
                    source=f"google_news/{category}",
                    original_id=str(hash(link)),
                    title=item.find("title").text,
                    content=item.find("pubDate").text,
                    link=link,
                    engagement=50,
                    preset_category=category
                ))
                count += 1
                if count >= 5: break

        except Exception as e:
            print(f"Google News collection error ({category}): {e}")

    return all_trends
