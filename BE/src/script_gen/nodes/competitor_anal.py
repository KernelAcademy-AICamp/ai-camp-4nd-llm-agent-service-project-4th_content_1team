"""
Competitor Analyzer Node - 경쟁 영상 분석 에이전트
YT Fetcher가 찾은 영상들을 분석하여 훅, 구조, 약점 등을 파악합니다.
"""

import logging
from typing import Dict, Any, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from src.script_gen.schemas.competitor import CompetitorAnalysisResult, VideoAnalysis, CrossInsights

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

MODEL_NAME = "gpt-4o-mini"


def competitor_anal_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    경쟁 영상을 분석하여 인사이트를 추출하는 노드
    
    Input (from state):
        - youtube_data: YT Fetcher가 검색한 영상 리스트
        - topic: 주제
    
    Output (to state):
        - competitor_data: CompetitorAnalysisResult (Schema 준수)
    """
    logger.info("Competitor Analyzer Node 시작")
    
    # 1. 입력 데이터 추출
    youtube_data = state.get("youtube_data", {})
    videos = youtube_data.get("videos", [])
    topic = state.get("topic", "")
    
    if not videos:
        logger.warning("분석할 영상이 없음 - 빈 결과 반환")
        return {"competitor_data": None}
    
    logger.info(f"분석 대상: {len(videos)}개 영상")
    
    # 2. 영상 분석 (LLM 사용)
    try:
        analysis_result = _analyze_competitors(videos[:5], topic)  # 상위 5개만 분석
        
        logger.info(f"분석 완료: {len(analysis_result.video_analyses)}개 영상")
        
        return {
            "competitor_data": analysis_result.model_dump()
        }
        
    except Exception as e:
        logger.error(f"경쟁사 분석 실패: {e}", exc_info=True)
        return {"competitor_data": None}


def _analyze_competitors(videos: List[Dict], topic: str) -> CompetitorAnalysisResult:
    """
    LLM을 사용하여 경쟁 영상 분석
    
    Args:
        videos: 영상 정보 리스트
        topic: 주제
    
    Returns:
        CompetitorAnalysisResult
    """
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0.3)
    structured_llm = llm.with_structured_output(CompetitorAnalysisResult)
    
    # Context 조립
    context_str = f"## TOPIC\n{topic}\n\n## COMPETITOR VIDEOS\n"
    for i, v in enumerate(videos, 1):
        context_str += f"{i}. [{v.get('title')}]\n"
        context_str += f"   - Channel: {v.get('channel_title')}\n"
        context_str += f"   - Views: {v.get('view_count'):,}\n"
        context_str += f"   - Likes: {v.get('like_count'):,}\n"
        context_str += f"   - URL: {v.get('url')}\n\n"
    
    system_prompt = """You are a YouTube content strategist analyzing competitor videos.

**TASK**: Analyze the provided videos and extract:
1. **Individual Video Insights**: Hook strategy, success factors, weak points
2. **Cross-Video Patterns**: Common gaps, formatting do's/don'ts

**OUTPUT**: CompetitorAnalysisResult object with detailed analysis.
"""

    user_prompt = f"""
{context_str}

**INSTRUCTIONS**:
- Analyze each video's hook, structure, and engagement factors
- Identify common gaps across all videos (what they missed)
- Extract formatting best practices and anti-patterns
- Focus on actionable insights for creating a differentiated video

Generate the CompetitorAnalysisResult now.
"""
    
    return structured_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])


# =============================================================================
# Helper: 실제 자막 분석 (Phase 2)
# =============================================================================

# def _analyze_with_transcripts(videos: List[Dict]) -> CompetitorAnalysisResult:
#     """
#     자막을 포함한 심층 분석 (Phase 2)
#     app/services/subtitle_service.py 활용
#     """
#     from app.services.subtitle_service import SubtitleService
#     
#     for video in videos:
#         video_id = video.get("video_id")
#         # 자막 추출
#         transcript = await SubtitleService.fetch_subtitle(video_id)
#         video["transcript"] = transcript
#     
#     # LLM에게 자막 포함하여 분석 요청
#     # ...
