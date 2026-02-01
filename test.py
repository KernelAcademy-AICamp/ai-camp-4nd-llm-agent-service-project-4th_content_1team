"""
Reddit 403 우회 - 자연스러운 접근 방식
두 번째 코드의 성공 원리를 적용한 심플 버전
"""

import requests
import time
import random
import pandas as pd
from typing import List, Optional, Dict

# User-Agent 리스트 (랜덤 선택용)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
]


def fetch_reddit_simple(subreddit: str, limit: int = 25) -> Optional[Dict]:
    """
    심플하게 Reddit JSON 가져오기
    - User-Agent만 사용
    - 복잡한 헤더 없음
    - 한 번에 요청
    """
    url = f"https://www.reddit.com/r/{subreddit}/hot.json"
    
    # 헤더는 User-Agent 하나만!
    headers = {
        "User-Agent": random.choice(USER_AGENTS)
    }
    
    params = {
        "limit": limit
    }
    
    try:
        # 429 방지용 짧은 대기
        time.sleep(1)
        
        print(f"  🔗 요청 URL: {url}")
        print(f"  📋 User-Agent: {headers['User-Agent'][:50]}...")
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        # 상세 디버깅 출력
        print(f"  📡 상태코드: {response.status_code}")
        print(f"  📦 Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        
        if response.status_code == 200:
            print(f"  ✓ 성공!")
            return response.json()
        elif response.status_code == 403:
            print(f"  ✗ 403 Forbidden - 접근 거부됨")
            print(f"  응답: {response.text[:300]}")
        elif response.status_code == 429:
            print(f"  ✗ 429 Too Many Requests - 요청 제한 초과")
            print(f"  응답: {response.text[:300]}")
        else:
            print(f"  ✗ 예상치 못한 상태코드")
            print(f"  응답 내용: {response.text[:300]}")
        
        return None
            
    except requests.exceptions.Timeout:
        print(f"  ✗ Timeout 에러: 서버 응답 없음 (10초 초과)")
        return None
    except requests.exceptions.ConnectionError:
        print(f"  ✗ 연결 에러: 인터넷 연결 확인 필요")
        return None
    except Exception as e:
        print(f"  ✗ 예외 발생: {type(e).__name__}: {e}")
        return None


def crawl_reddit_natural(subreddits: List[str], max_posts_per_sub: int = 50) -> pd.DataFrame:
    """
    자연스러운 Reddit 크롤링
    - 재시도 없음
    - 실패하면 그냥 넘어감
    - 심플한 로직
    """
    all_posts = []
    
    for i, subreddit in enumerate(subreddits, 1):
        print(f"\n[{i}/{len(subreddits)}] r/{subreddit} 수집 중...")
        
        # 한 번만 시도
        data = fetch_reddit_simple(subreddit, limit=min(max_posts_per_sub, 100))
        
        if not data:
            print(f"  ✗ 건너뜀")
            continue
        
        # 포스트 추출
        children = data.get("data", {}).get("children", [])
        
        if not children:
            print(f"  ✗ 데이터 없음")
            continue
        
        collected = 0
        for child in children:
            post_data = child.get("data", {})
            
            # 광고나 고정글 제외
            if post_data.get("stickied") or post_data.get("score", 0) < 10:
                continue
            
            all_posts.append({
                "subreddit": subreddit,
                "id": post_data.get("id"),
                "title": post_data.get("title", ""),
                "selftext": post_data.get("selftext", "")[:300],  # 300자만
                "score": post_data.get("score", 0),
                "num_comments": post_data.get("num_comments", 0),
                "created_utc": post_data.get("created_utc", 0),
                "author": post_data.get("author", ""),
                "url": post_data.get("url", ""),
            })
            
            collected += 1
            if collected >= max_posts_per_sub:
                break
        
        print(f"  ✓ {collected}개 수집")
        
        # 서브레딧 간 1초만 대기 (자연스럽게)
        if i < len(subreddits):
            time.sleep(1)
    
    # DataFrame 생성
    df = pd.DataFrame(all_posts)
    
    # Score 순으로 정렬
    if not df.empty:
        df = df.sort_values("score", ascending=False).reset_index(drop=True)
    
    return df


def main():
    """실행 함수"""
    print("=" * 80)
    print("Reddit 자연스러운 크롤러")
    print("=" * 80)
    
    # 테스트할 서브레딧
    test_subreddits = ["technology", "programming", "worldnews"]
    
    # 크롤링 실행
    df = crawl_reddit_natural(test_subreddits, max_posts_per_sub=30)
    
    if not df.empty:
        # 중복 제거
        df = df.drop_duplicates(subset=['id'], keep='first')
        
        # 저장
        output = "reddit_posts_natural.csv"
        df.to_csv(output, index=False, encoding="utf-8-sig")
        
        print(f"\n{'=' * 80}")
        print(f"✓ 성공! {len(df)}개 포스트 수집")
        print(f"✓ 파일: {output}")
        print(f"{'=' * 80}")
        
        # 통계
        print("\n📊 서브레딧별 수집:")
        print(df['subreddit'].value_counts())
        
        print("\n🔥 인기 포스트 TOP 5:")
        for idx, row in df.head(5).iterrows():
            print(f"  [{row['score']:>5} 점] [{row['subreddit']:>15}] {row['title'][:50]}...")
        
    else:
        print(f"\n{'=' * 80}")
        print("✗ 수집 실패")
        print(f"{'=' * 80}")
        print("\n💡 해결 방법:")
        print("1. VPN 켜고 다시 시도")
        print("2. 다른 시간대에 시도 (미국 시간 기준 오전/오후)")
        print("3. 서브레딧 이름 확인 (대소문자, 철자)")
        print("4. IP가 일시 차단되었을 수 있음 → 30분 후 재시도")


if __name__ == "__main__":
    main()