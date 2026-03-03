"""
Competitor Analyzer Node - 경쟁 영상 분석 에이전트
YT Fetcher가 찾은 영상들을 분석하여 성공이유, 부족한점, 적용포인트, 시청자반응을 파악합니다.

분석 페이지(competitor_channel_service.py)와 동일한 방식:
- gpt-4.1 모델
- 자막 텍스트 기반 분석
- 동일한 프롬프트
"""

import logging
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from app.services.subtitle_service import SubtitleService
from app.core.config import settings

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

MODEL_NAME = "gpt-4.1"


async def competitor_anal_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    경쟁 영상을 분석하여 인사이트를 추출하는 노드

    분석 페이지(competitor_channel_service.py)와 동일한 방식 사용:
    - 자막 텍스트 기반 분석
    - gpt-4.1 모델
    - 동일한 프롬프트
    """
    logger.info("Competitor Analyzer Node 시작")

    youtube_data = state.get("youtube_data", {})
    videos = youtube_data.get("videos", [])
    topic = state.get("topic", "")

    if not videos:
        logger.warning("분석할 영상이 없음 - 빈 결과 반환")
        return {"competitor_data": None}

    target_videos = videos[:5]
    logger.info(f"분석 대상: {len(target_videos)}개 영상")

    video_analyses = []

    for video in target_videos:
        try:
            analysis = await _analyze_single_video(video, topic)
            if analysis:
                video_analyses.append(analysis)
        except Exception as e:
            logger.warning(f"영상 분석 실패 ({video.get('video_id')}): {e}")
            continue

    logger.info(f"분석 완료: {len(video_analyses)}개 영상")

    result = {
        "video_analyses": video_analyses,
        "analyzed_at": datetime.utcnow().isoformat(),
    }

    return {"competitor_data": result}


async def _analyze_single_video(video: Dict, topic: str) -> Optional[Dict]:
    """
    단일 영상 분석 (분석 페이지 competitor_channel_service.py와 동일한 로직)
    1. 자막 가져오기
    2. gpt-4.1로 분석 (동일 프롬프트)
    """
    video_id = video.get("video_id", "")
    title = video.get("title", "")

    # 1. 자막 가져오기
    caption_text = ""
    try:
        results = await SubtitleService.fetch_subtitles(
            video_ids=[video_id],
            languages=["ko", "en"],
            db=None,
        )
        if results:
            fetch_result = results[0]
            tracks = fetch_result.get("tracks", [])
            for track in tracks:
                for cue in track.get("cues", []):
                    caption_text += cue.get("text", "") + " "
            caption_text = caption_text.strip()

            # 자막 길이 제한 (분석 페이지와 동일: 12,000자)
            max_chars = 12000
            if len(caption_text) > max_chars:
                caption_text = caption_text[:max_chars] + "..."

            if caption_text:
                logger.info(f"자막 가져오기 성공 ({video_id}): {len(caption_text)}자")
    except Exception as e:
        logger.warning(f"자막 가져오기 실패 ({video_id}): {e}")

    if not caption_text:
        logger.info(f"자막 없음, 메타데이터로 분석: {video_id}")
        caption_text = (
            f"(자막 없음 - 영상 제목과 메타데이터만으로 분석)\n"
            f"제목: {title}\n"
            f"채널: {video.get('channel_title', '')}\n"
            f"조회수: {video.get('view_count', 0):,}"
        )

    # 2. LLM 분석 (분석 페이지와 동일한 프롬프트)
    api_key = settings.openai_api_key
    if not api_key:
        logger.error("OpenAI API 키가 설정되지 않았습니다.")
        return None

    llm = ChatOpenAI(model=MODEL_NAME, api_key=api_key)

    prompt = f"""당신은 전문 유튜브 콘텐츠 분석가입니다. 경쟁 유튜버의 영상 자막을 분석하여 4가지를 알려주세요.

분석 대상 영상 제목: {title}

[자막 트랜스크립트]
{caption_text}

분석 지침:
1. "strengths" — 이 영상이 잘 된 이유 3~5개. 구체적 근거(자막 내용 인용)를 반드시 포함.
2. "weaknesses" — 이 영상에서 아쉬운 점 2~4개. "왜냐하면", "예를 들어" 등으로 구체적 이유를 반드시 포함.
3. "applicable_points" — 내 채널에 적용할 수 있는 구체적 액션 아이템 3~5개. 일반적인 유튜브 채널에 적용할 수 있도록 제안해주세요.
4. "comment_insights" — 자막 내용에서 예상되는 시청자 반응과 니즈를 추론해주세요:
   - "reactions": 시청자들의 주요 반응 3~5개 (긍정/부정/요청 등)
   - "needs": 시청자들이 원하는 콘텐츠/니즈 2~4개

작성 스타일:
- 한국어로 작성
- 쉽고 자연스러운 구어체 사용
- 구체적이고 실용적으로 작성 (추상적 표현 금지)
- 각 항목은 1~2문장으로 간결하게

출력 형식 (JSON만 출력, 다른 텍스트 없이):
{{
  "strengths": ["성공이유1", "성공이유2", ...],
  "weaknesses": ["부족한점1", "부족한점2", ...],
  "applicable_points": ["적용포인트1", "적용포인트2", ...],
  "comment_insights": {{
    "reactions": ["시청자 반응1", "시청자 반응2", ...],
    "needs": ["시청자 니즈1", "시청자 니즈2", ...]
  }}
}}"""

    try:
        res = await llm.ainvoke([HumanMessage(content=prompt)])
        content = res.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(content)

        # video_id, title 추가
        parsed["video_id"] = video_id
        parsed["title"] = title

        logger.info(f"영상 분석 완료: {video_id} - {title[:30]}")
        return parsed

    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"LLM 분석 파싱 실패 ({video_id}): {e}")
        return None
