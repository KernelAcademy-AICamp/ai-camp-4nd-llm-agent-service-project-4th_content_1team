"""
Script Generation Graph - LangGraph 워크플로우
주제(Topic)를 입력받아 유튜브 대본(Script)을 생성하는 전체 파이프라인

Workflow (Full Pipeline):
    User Input (Topic + Channel Profile)
    → Planner (목차/질문 생성)
    ┌→ News Research (뉴스 수집 + 크롤링)
    │   → Article Analyzer (기사별 팩트·의견·해석 추출)
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
from src.script_gen.nodes.intent_analyzer import intent_node
from src.script_gen.nodes.planner import planner_node
from src.script_gen.nodes.news_research import news_research_node
from src.script_gen.nodes.article_analyzer import article_analyzer_node
from src.script_gen.nodes.yt_fetcher import yt_fetcher_node
from src.script_gen.nodes.competitor_anal import competitor_anal_node
# from src.script_gen.nodes.insight_builder import insight_builder_node
from src.script_gen.nodes.insight_builder_2 import insight_builder_node  
from src.script_gen.nodes.writer import writer_node
from src.script_gen.nodes.verifier import verifier_node
# from src.script_gen.nodes.trend_scout import trend_scout_node  # 주석처리: topic_recommendations로 대체

logger = logging.getLogger(__name__)


# =============================================================================
# Graph Construction
# =============================================================================

def create_script_gen_graph():
    """Script Generation Graph 생성 (전체 파이프라인)"""

    # 1. Graph 초기화
    workflow = StateGraph(ScriptGenState)

    # 2. 노드 추가
    workflow.add_node("intent_analyzer", intent_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("news_research", news_research_node)
    workflow.add_node("article_analyzer", article_analyzer_node)  # 기사 심층 분석
    workflow.add_node("yt_fetcher", yt_fetcher_node)
    workflow.add_node("competitor_anal", competitor_anal_node)
    workflow.add_node("insight_builder", insight_builder_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("verifier", verifier_node)

    # 3. 엣지 연결
    workflow.set_entry_point("intent_analyzer")
    workflow.add_edge("intent_analyzer", "planner")

    # Planner 후 병렬 실행: News Research 와 YT Fetcher
    workflow.add_edge("planner", "news_research")
    workflow.add_edge("planner", "yt_fetcher")

    # News Research → Article Analyzer (기사 수집 후 팩트·의견 추출)
    workflow.add_edge("news_research", "article_analyzer")

    # YT Fetcher → Competitor Analyzer
    workflow.add_edge("yt_fetcher", "competitor_anal")

    # Article Analyzer 와 Competitor Analyzer 모두 완료 후 Insight Builder
    # (LangGraph 가 두 선행 노드를 자동으로 기다림)
    workflow.add_edge("article_analyzer", "insight_builder")
    workflow.add_edge("competitor_anal", "insight_builder")

    workflow.add_edge("insight_builder", "writer")
    workflow.add_edge("writer", "verifier")
    workflow.add_edge("verifier", END)

    # 4. 컴파일
    app = workflow.compile()

    logger.info("Script Generation Graph 생성 완료 (Full Pipeline: 9 nodes)")
    return app


# =============================================================================
# Execution Function
# =============================================================================

# =============================================================================
# 노드 이름 → 사용자 표시용 매핑
# =============================================================================

PIPELINE_STEPS = [
    {"key": "intent_analyzer",  "label": "시청자 의도 분석",                   "emoji": "🎯", "nodes": ["intent_analyzer"]},
    {"key": "planner",          "label": "콘텐츠 기획안 작성",                 "emoji": "📋", "nodes": ["planner"]},
    {"key": "research",         "label": "뉴스 기사 수집 및 유튜브 영상 검색", "emoji": "📰", "nodes": ["news_research", "yt_fetcher"]},
    {"key": "analysis",         "label": "기사 심층 분석 및 경쟁 영상 분석",   "emoji": "🔍", "nodes": ["article_analyzer", "competitor_anal"]},
    {"key": "insight_builder",  "label": "전략 인사이트 수립",                 "emoji": "💡", "nodes": ["insight_builder"]},
    {"key": "writer",           "label": "스크립트 작성",                      "emoji": "✍️", "nodes": ["writer"]},
    {"key": "verifier",         "label": "팩트 체크 검증",                     "emoji": "✅", "nodes": ["verifier"]},
]

# 노드 이름 → 스텝 key 역매핑
_NODE_TO_STEP = {}
for _step in PIPELINE_STEPS:
    for _node in _step["nodes"]:
        _NODE_TO_STEP[_node] = _step["key"]

ALL_NODE_NAMES = list(_NODE_TO_STEP.keys())


async def generate_script(
    topic: str,
    channel_profile: dict,
    topic_request_id: str = None,
    progress_callback=None,
) -> dict:
    """
    주제를 입력받아 전체 파이프라인을 실행합니다.

    Args:
        topic: 사용자가 입력한 주제 (예: "AI 반도체 시장 동향")
        channel_profile: 채널 정보 (name, tone, target_audience 등)
        topic_request_id: 요청 ID (선택)
        progress_callback: 진행 상황 콜백 (step_key, status) → Celery update_state용

    Returns:
        ScriptDraft dict (최종 대본, news_data, competitor_data 포함)
    """
    import uuid

    if not topic_request_id:
        topic_request_id = f"trq_{uuid.uuid4().hex[:8]}"

    # 초기 State 구성
    initial_state = {
        "topic": topic,
        "topic_request_id": topic_request_id,
        "channel_profile": channel_profile,
        "intent_analysis": {},
        "trend_data": {},
        "content_brief": {},
        "news_data": {},
        "insight_pack": {},
        "script_draft": {},
        "competitor_data": None,
        "youtube_data": None
    }

    logger.info(f"Script Generation 시작: {topic!r}")
    logger.info(f"[Graph] 노드 목록: intent_analyzer → planner → [news_research + yt_fetcher 병렬] → ...")
    app = create_script_gen_graph()

    try:
        # astream_events로 노드 진입/완료 이벤트를 실시간 수신
        final_state = None
        completed_nodes = set()    # 개별 노드 완료 추적
        completed_steps = []       # UI 스텝 완료 추적

        def _notify(current_step_key, message):
            """진행 상황을 콜백으로 전달"""
            if progress_callback:
                progress_callback(
                    current_step=current_step_key,
                    message=message,
                    completed_steps=list(completed_steps),
                )

        async for event in app.astream_events(initial_state, version="v2"):
            kind = event.get("event", "")
            name = event.get("name", "")

            if name not in ALL_NODE_NAMES:
                # 최종 결과 수집
                if kind == "on_chain_end" and event.get("data", {}).get("output"):
                    output = event["data"]["output"]
                    if isinstance(output, dict) and "script_draft" in output:
                        final_state = output
                continue

            step_key = _NODE_TO_STEP[name]
            step_info = next(s for s in PIPELINE_STEPS if s["key"] == step_key)

            # 노드 시작 이벤트
            if kind == "on_chain_start":
                if step_key not in completed_steps:
                    _notify(step_key, f"{step_info['emoji']} {step_info['label']} 중...")
                logger.info(f"▶ Node 시작: {name}")

            # 노드 완료 이벤트
            elif kind == "on_chain_end":
                completed_nodes.add(name)
                logger.info(f"✓ Node 완료: {name}")

                # 그룹 내 모든 노드가 완료되었는지 확인
                group_nodes = set(step_info["nodes"])
                if group_nodes.issubset(completed_nodes) and step_key not in completed_steps:
                    completed_steps.append(step_key)
                    _notify(step_key, f"{step_info['emoji']} {step_info['label']} 완료")

        if final_state is None:
            raise RuntimeError("파이프라인이 결과를 반환하지 않았습니다.")

        logger.info("Script Generation 완료")

        # yt_fetcher 실행 여부 확인 및 관련 영상 정리
        yt_data = final_state.get("youtube_data") or {}
        logger.info(f"[Graph] youtube_data 존재: {bool(yt_data)}")

        related_videos: list[dict] = []
        try:
            from datetime import datetime, timezone

            videos = yt_data.get("videos", []) or []
            queries_used = yt_data.get("search_queries_used", []) or []

            # 인기순(조회수) + 키워드 관련도(검색 쿼리) + 기간당 조회수(view_velocity) 계산
            for idx, v in enumerate(videos[:2]):  # 상위 2개만 사용
                vid = v.get("video_id")
                if not vid:
                    continue

                published_at = v.get("published_at") or ""
                view_count = int(v.get("view_count", 0) or 0)

                velocity = 0.0
                if published_at:
                    try:
                        pub_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                        days = max((datetime.now(timezone.utc) - pub_dt).days, 1)
                        velocity = view_count / days
                    except Exception:
                        velocity = 0.0

                search_keyword = queries_used[idx] if idx < len(queries_used) else ""

                related_videos.append(
                    {
                        "video_id": vid,
                        "title": v.get("title", ""),
                        "channel": v.get("channel_title", ""),
                        "url": v.get("url") or f"https://www.youtube.com/watch?v={vid}",
                        "thumbnail": f"https://img.youtube.com/vi/{vid}/mqdefault.jpg",
                        "view_count": view_count,
                        "published_at": published_at,
                        "view_velocity": round(velocity, 1),
                        "search_keyword": search_keyword,
                        "search_type": "popular",
                    }
                )

            logger.info(f"[Graph] related_videos 구성: {len(related_videos)}개")
        except Exception as e:
            logger.warning(f"[Graph] related_videos 생성 실패: {e}")

        # related_videos에 competitor 분석 결과 매칭 (같은 youtube_data에서 왔으므로 video_id 동일)
        competitor_data = final_state.get("competitor_data") or {}
        if competitor_data:
            video_analyses = competitor_data.get("video_analyses", [])
            # video_id → 분석 결과 매핑
            analysis_map = {}
            for va in video_analyses:
                vid = va.get("video_id")
                if vid:
                    analysis_map[vid] = va
            
            for rv in related_videos:
                analysis = analysis_map.get(rv["video_id"])
                if analysis:
                    rv["strengths"] = analysis.get("strengths", [])
                    rv["weaknesses"] = analysis.get("weaknesses", [])
                    rv["applicable_points"] = analysis.get("applicable_points", [])
                    rv["comment_insights"] = analysis.get("comment_insights", {})
                    logger.info(f"[Graph] related_video '{rv['title'][:30]}' 에 분석 결과 매칭 완료")

        # 전체 파이프라인 결과
        result = final_state["script_draft"].copy()
        result["verifier_output"] = final_state.get("verifier_output")
        result["news_data"] = final_state.get("news_data")
        result["competitor_data"] = final_state.get("competitor_data")
        result["youtube_data"] = yt_data
        result["related_videos"] = related_videos
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
    
    import asyncio
    print(f"🚀 테스트 시작: {test_topic}")
    result = asyncio.run(generate_script(test_topic, test_channel))
    
    print("\n✅ 대본 생성 완료!")
    print(f"- Script ID: {result.get('script_draft_id')}")
    print(f"- 챕터 수: {len(result.get('script', {}).get('chapters', []))}")
    print(f"- Hook: {result.get('script', {}).get('hook', {}).get('text', '')[:100]}...")
