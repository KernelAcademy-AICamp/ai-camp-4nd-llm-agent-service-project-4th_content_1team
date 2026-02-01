import logging
import json
import os
from src.script_gen.nodes.trend_scout import trend_scout_node
from src.script_gen.nodes.planner import planner_node
from src.script_gen.nodes.news_research import news_research_node
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_integration_pipeline():
    """
    [통합 테스트]
    Trend Scout -> Planner -> News Research (Optional)
    전체 흐름이 유기적으로 연결되는지 검증합니다.
    """
    load_dotenv()
    
    # 1. 초기 상태 설정 (사용자 입력 가정)
    initial_state = {
        "channel_profile": {
            "name": "Tech Future",
            "category": "Technology & AI",
            "target_audience": "Tech enthusiasts, Early adopters",
            "average_duration": 10,
            "content_style": "Deep Dive Analysis with cynicism" # 약간 삐딱한 분석 스타일
        },
        # topic은 Trend Scout가 찾아줄 것이므로 비워둠 (혹은 관심사 설정)
        "channel_profile_interests": ["Artificial Intelligence", "Gadgets", "Future Tech"]
    }
    
    logger.info("🎬 [Step 1] Trend Scout: 트렌드 발굴 및 여론 수집 시작")
    state_after_trend = trend_scout_node(initial_state)
    
    # Trend Scout 결과 확인
    topic = state_after_trend.get("topic")
    trend_data = state_after_trend.get("trend_analysis", {})
    
    if not topic:
        logger.error("❌ Trend Scout가 주제를 찾지 못했습니다. 파이프라인 중단.")
        return

    logger.info(f"✅ 선정된 주제: {topic}")
    logger.info(f"✅ 트렌드 분석 데이터 확보: 키워드 {len(trend_data.get('keywords', []))}개")
    if "top_comments" in trend_data:
        logger.info(f"✅ 수집된 베스트 댓글: {len(trend_data['top_comments'])}개 확인됨")
        # 댓글 샘플 출력 (번역 및 좋아요 확인)
        for i, c in enumerate(trend_data["top_comments"][:2]):
            logger.info(f"   💬 Comment #{i+1}: {c[:50]}...")

    print("\n" + "="*50 + "\n")

    # 2. Planner 실행 (Trend Data 반영)
    logger.info("🎬 [Step 2] Planner: 여론 반영 기획안 수립 시작")
    
    # Planner가 trend_analysis를 쓸 수 있도록 state가 잘 전달되는지 확인
    # (planner_node 내부에서 state['trend_analysis']를 참조하도록 수정했는지 체크 필요.
    #  아까 _build_planner_prompt 인자만 추가했지, node 함수 자체에서 넘겨주는 로직을 확인해야 함.
    #  -> 만약 planner.py의 planner_node 함수에서 trend_analysis를 추출해서 _build_planner_prompt에 안 넘겨주면 반영 안 됨.
    #  -> **중요**: planner.py의 node 함수 수정이 필요할 수 있음. 일단 돌려보고 확인.)
    
    try:
        state_after_planner = planner_node(state_after_trend)
        content_brief = state_after_planner.get("content_brief")
        
        logger.info("✅ 기획안(Content Brief) 생성 완료")
        logger.info(json.dumps(content_brief, indent=2, ensure_ascii=False))
        
        # 기획안 검증: Trend가 반영되었나?
        # 사람이 직접 눈으로 봐야 알 수 있음 (Context에 들어갔는지 로그로 확인 등)

    except Exception as e:
        logger.error(f"❌ Planner 실행 중 오류: {e}")
        return

    print("\n" + "="*50 + "\n")

    # 3. News Research 실행 (기획안 기반 팩트 수집)
    logger.info("🎬 [Step 3] News Research: 팩트 & 핵심 문단 수집 시작")
    # News Research는 content_brief['researchPlan']을 사용함
    
    try:
        # 시간 절약을 위해 쿼리 1개만 남기고 테스트 (실제로는 다 돌림)
        if content_brief and "researchPlan" in content_brief:
             original_queries = content_brief["researchPlan"].get("newsQuery", [])
             content_brief["researchPlan"]["newsQuery"] = original_queries[:1] # 테스트용 1개만
             logger.info(f"🧪 테스트 모드: 첫 번째 쿼리 '{original_queries[0]}'만 실행합니다.")

        state_after_news = news_research_node(state_after_planner)
        news_data = state_after_news.get("news_data", {})
        articles = news_data.get("articles", [])
        
        logger.info(f"✅ 수집된 기사 수: {len(articles)}개")
        for i, art in enumerate(articles):
            logger.info(f"📄 Article #{i+1}: {art['title']}")
            logger.info(f"   - 핵심 문단(Summary) 길이: {len(art.get('summary', ''))}자")
            logger.info(f"   - 차트: {len(art.get('charts', []))}개 / 이미지: {len(art.get('images', []))}개")
            if art.get("summary"):
                logger.info(f"   📝 Summary Preview: {art['summary'][:100]}...")

    except Exception as e:
        logger.error(f"❌ News Research 실행 중 오류: {e}")
        return

    print("\n" + "="*50 + "\n")
    logger.info("🎉 통합 파이프라인 테스트 완료!")

if __name__ == "__main__":
    test_integration_pipeline()
