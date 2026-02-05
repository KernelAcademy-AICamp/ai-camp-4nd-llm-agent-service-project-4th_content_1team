"""
Script Generation Graph - LangGraph 워크플로우
주제(Topic)를 입력받아 유튜브 대본(Script)을 생성하는 전체 파이프라인

Workflow (Full Pipeline):
    User Input (Topic + Channel Profile)
    → Planner (목차/질문 생성)
    ┌→ News Research (뉴스 수집 + Fact Extraction)
    └→ YT Fetcher (유튜브 영상 검색)
       → Competitor Analyzer (경쟁사 분석)
    → Insight Builder (전략 수립)
    → Writer (대본 작성)
    → Verifier (팩트 체크 & 출처 정리)
    → Output (Verified ScriptDraft)

Note: Trend Scout는 topic_recommendations로 대체됨 (주석처리)
"""

import logging
from langgraph.graph import StateGraph, END

from src.script_gen.state import ScriptGenState  # State 정의 import
from src.script_gen.nodes.planner import planner_node
from src.script_gen.nodes.news_research import news_research_node
from src.script_gen.nodes.yt_fetcher import yt_fetcher_node
from src.script_gen.nodes.competitor_anal import competitor_anal_node
from src.script_gen.nodes.insight_builder import insight_builder_node
from src.script_gen.nodes.writer import writer_node
from src.script_gen.nodes.verifier import verifier_node
# from src.script_gen.nodes.trend_scout import trend_scout_node  # 주석처리: topic_recommendations로 대체

logger = logging.getLogger(__name__)


# =============================================================================
# Graph Construction
# =============================================================================

def create_script_gen_graph():
    """Script Generation Graph 생성"""
    
    # 1. Graph 초기화
    workflow = StateGraph(ScriptGenState)
    
    # 2. 노드 추가
    # workflow.add_node("trend_scout", trend_scout_node)  # 주석처리: topic_recommendations로 대체
    workflow.add_node("planner", planner_node)
    workflow.add_node("news_research", news_research_node)
    workflow.add_node("yt_fetcher", yt_fetcher_node)
    workflow.add_node("competitor_anal", competitor_anal_node)
    workflow.add_node("insight_builder", insight_builder_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("verifier", verifier_node)
    
    # 3. 엣지 연결
    workflow.set_entry_point("planner")  # Planner를 시작점으로 변경
    # workflow.add_edge("trend_scout", "planner")  # 주석처리
    
    # Planner 후 병렬 실행: News Research와 YT Fetcher
    workflow.add_edge("planner", "news_research")
    workflow.add_edge("planner", "yt_fetcher")
    
    # YT Fetcher → Competitor Analyzer
    workflow.add_edge("yt_fetcher", "competitor_anal")
    
    # News Research와 Competitor Analyzer 모두 완료 후 Insight Builder
    # (LangGraph는 자동으로 모든 선행 노드 완료를 기다림)
    workflow.add_edge("news_research", "insight_builder")
    workflow.add_edge("competitor_anal", "insight_builder")
    
    workflow.add_edge("insight_builder", "writer")
    workflow.add_edge("writer", "verifier")
    workflow.add_edge("verifier", END)
    
    # 4. 컴파일
    app = workflow.compile()
    
    logger.info("Script Generation Graph 생성 완료 (Full Pipeline: 7 nodes)")
    return app


# =============================================================================
# Execution Function
# =============================================================================

def generate_script(
    topic: str,
    channel_profile: dict,
    topic_request_id: str = None
) -> dict:
    """
    주제를 입력받아 전체 파이프라인을 실행하고 대본을 생성합니다.
    
    Args:
        topic: 사용자가 입력한 주제 (예: "AI 반도체 시장 동향")
        channel_profile: 채널 정보 (name, tone, target_audience 등)
        topic_request_id: 요청 ID (선택)
    
    Returns:
        ScriptDraft dict (최종 대본)
    """
    import uuid
    
    if not topic_request_id:
        topic_request_id = f"trq_{uuid.uuid4().hex[:8]}"
    
    # 초기 State 구성
    initial_state = {
        "topic": topic,
        "topic_request_id": topic_request_id,
        "channel_profile": channel_profile,
        "trend_data": {},
        "content_brief": {},
        "news_data": {},
        "insight_pack": {},
        "script_draft": {},
        "competitor_data": None,
        "youtube_data": None
    }
    
    # Graph 실행
    logger.info(f"Script Generation 시작: {topic}")
    app = create_script_gen_graph()
    
    try:
        final_state = app.invoke(initial_state)
        logger.info("Script Generation 완료")
        
        # ScriptDraft + VerifierOutput + NewsData + CompetitorData 반환
        result = final_state["script_draft"].copy()
        result["verifier_output"] = final_state.get("verifier_output")
        result["news_data"] = final_state.get("news_data")
        result["competitor_data"] = final_state.get("competitor_data")  # 경쟁 영상 분석 결과 추가
        
        return result
    
    except Exception as e:
        logger.error(f"Script Generation 실패: {e}", exc_info=True)
        raise


# =============================================================================
# CLI Test (개발용)
# =============================================================================

if __name__ == "__main__":
    # 간단한 테스트 실행
    test_topic = "AI 반도체 시장의 최신 동향"
    test_channel = {
        "name": "테크 인사이트",
        "tone": "분석적이지만 쉬운",
        "target_audience": "IT 관심 일반인",
        "category": "Technology"
    }
    
    print(f"🚀 테스트 시작: {test_topic}")
    result = generate_script(test_topic, test_channel)
    
    print("\n✅ 대본 생성 완료!")
    print(f"- Script ID: {result.get('script_draft_id')}")
    print(f"- 챕터 수: {len(result.get('script', {}).get('chapters', []))}")
    print(f"- Hook: {result.get('script', {}).get('hook', {}).get('text', '')[:100]}...")
