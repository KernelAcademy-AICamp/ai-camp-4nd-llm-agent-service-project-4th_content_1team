
import os
import sys
import json
import logging
from dotenv import load_dotenv

# 프로젝트 루트를 Python Path에 추가
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.script_gen.nodes.news_research import news_research_node

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_news_only():
    print("=" * 50)
    print("📰 News Research Node 단독 테스트")
    print("=" * 50)
    
    load_dotenv()
    
    if not os.getenv("TAVILY_API_KEY"):
        print("⚠️ TAVILY_API_KEY가 없습니다. .env를 확인해주세요.")
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️ OPENAI_API_KEY가 없습니다. .env를 확인해주세요.")

    # 테스트 입력 데이터
    mock_state = {
        "content_brief": {
            "researchPlan": {
                "newsQuery": ["2026년 부동산 시장 전망", "강남 아파트 가격 추이"]
            }
        }
    }
    
    print(f"검색어: {mock_state['content_brief']['researchPlan']['newsQuery']}")
    print("⏳ 뉴스 수집 및 AI 분석 중... (약 30초~1분 소요)")
    
    try:
        result = news_research_node(mock_state)
        news_data = result.get("news_data", {})
        articles = news_data.get("articles", [])
        
        print(f"\n✅ 수집 완료: {len(articles)}개 기사")
        
        # 결과 확인
        for i, art in enumerate(articles, 1):
            print(f"\n[{i}] {art.get('source', 'Unknown')} - {art.get('title')}")
            print(f"   🔗 {art.get('url')}")
            print(f"   📝 1줄 요약: {art.get('summary_short')}")
            
            analysis = art.get('analysis', {})
            facts = analysis.get('facts', [])
            opinions = analysis.get('opinions', [])
            
            print(f"   🔵 Facts ({len(facts)}개):")
            for f in facts[:2]: print(f"      - {f}")
            
            print(f"   🟡 Opinions ({len(opinions)}개):")
            for o in opinions[:2]: print(f"      - {o}")

        # 파일 저장
        output_file = "test_news_result.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            
        print(f"\n💾 전체 결과 저장됨: {output_file}")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_news_only()
