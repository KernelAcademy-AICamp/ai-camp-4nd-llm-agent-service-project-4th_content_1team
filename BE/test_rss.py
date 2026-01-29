
import feedparser
import logging
import urllib.parse
import requests
from io import BytesIO

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_rss_with_headers(url):
    """
    User-Agent 헤더를 추가해서 RSS 데이터를 가져온 뒤 파싱
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 바이트 스트림을 feedparser에 전달
        return feedparser.parse(BytesIO(response.content))
    except Exception as e:
        print(f"Request failed: {e}")
        return None

def fetch_rss_test(query):
    print(f"\n======== RSS Test for query: '{query}' ========")
    
    encoded_query = urllib.parse.quote(query)
    
    # 네이버 뉴스 RSS (HTTPS + 헤더 사용)
    sources = [
        ("Naver News", f"https://newssearch.naver.com/search.naver?where=rss&query={encoded_query}"),
        # 구글은 원래 잘 되니까 비교용으로 유지
        ("Google News", f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko")
    ]
    
    for name, url in sources:
        print(f"\n--- Fetching from: {name} ---")
        print(f"URL: {url}")
        
        feed = fetch_rss_with_headers(url)
        
        if feed:
            if hasattr(feed, 'bozo_exception') and feed.bozo_exception:
                print(f"Warning: Parse error or malformed XML: {str(feed.bozo_exception)[:100]}")
            
            print(f"Found {len(feed.entries)} entries.")
            
            for i, entry in enumerate(feed.entries[:3], 1):
                print(f"{i}. [{entry.title}]")
                print(f"   Link: {entry.link}")
                pub_date = entry.get('published', entry.get('updated', 'N/A'))
                print(f"   Date: {pub_date}")

if __name__ == "__main__":
    fetch_rss_test("AI 반도체")
    fetch_rss_test("손흥민")
