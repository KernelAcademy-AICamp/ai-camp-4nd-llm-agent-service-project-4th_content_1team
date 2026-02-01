"""
트렌드 스카우트 노드 테스트 스크립트
API 키 없이 레딧 데이터(JSON)를 잘 긁어오는지, 그리고 한국어 키워드로 잘 변환하는지 확인합니다.
"""
import sys
import os
import logging
import json

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 경로 설정
sys.path.insert(0, os.path.dirname(__file__))

from src.script_gen.nodes.trend_scout import trend_scout_node

def run_test():
    print("=" * 60)
    print("🚀 트렌드 스카우트 (Trend Scout) 테스트 시작")
    print("=" * 60)

    # 테스트 케이스 1: 특정 관심사(AI/Tech)가 있는 경우
    print("\n[Scenario 1] 페르소나: AI & Tech 전문 채널")
    state_tech = {
        "channel_profile": {
            "topics": ["AI", "Technology"],
            "tone": "Expert"
        }
    }
    
    try:
        result_tech = trend_scout_node(state_tech)
        queries = result_tech["researchPlan"]["newsQuery"]
        print(f"✅ 추출된 검색어: {queries}")

        # [디버깅] 수집된 댓글 확인을 위해 내부 함수 직접 호출해보기
        print("\n🔍 [댓글 수집 데이터 검증]")
        from src.script_gen.nodes.trend_scout import _fetch_reddit_json, _determine_subreddits
        
        targets = _determine_subreddits(state_tech["channel_profile"]["topics"])
        raw_posts = _fetch_reddit_json(targets)
        
        for i, post in enumerate(raw_posts[:3]): # 상위 3개만 출력
            print(f"\n📌 Post #{i+1}: {post['title']}")
            print(f"   (Subreddit: r/{post['subreddit']}, Score: {post['score']})")
            if 'top_comments' in post and post['top_comments']:
                print("   💬 Top Comments:")
                for comment in post['top_comments']:
                    print(f"      - {comment}")
            else:
                print("   ⚠️ 댓글 없음 (또는 수집 실패)")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")

    # 테스트 케이스 2: 관심사가 없는 경우 (Fallback 작동 확인)
    print("\n[Scenario 2] 페르소나: 정보 없음 (기본값 테스트)")
    state_empty = {
        "channel_profile": {}  # Empty
    }
    
    try:
        result_empty = trend_scout_node(state_empty)
        queries = result_empty["researchPlan"]["newsQuery"]
        print(f"✅ 추출된 검색어 (Fallback): {queries}")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")

    print("\n" + "=" * 60)
    print("테스트 종료")

if __name__ == "__main__":
    run_test()
