"""
영상 자막 기반 분석 서비스

채널 영상의 자막을 분석하여 영상 유형, 콘텐츠 구조, 톤앤매너 등을 추출합니다.
페르소나 고도화에 사용됩니다.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple
import asyncio
import json
import re

import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.channel_video import YTChannelVideo, YTVideoStats
from app.models.yt_my_video_analysis import YTMyVideoAnalysis
from app.services.subtitle_service import SubtitleService
from app.services.youtube_service import YouTubeService

logger = logging.getLogger(__name__)


# ============================================================================
# 데이터 클래스
# ============================================================================

@dataclass
class VideoForAnalysis:
    """분석 대상 영상 정보."""
    id: str                    # YTChannelVideo.id (UUID)
    youtube_video_id: str      # YouTube video ID
    title: str
    view_count: int
    like_count: int
    comment_count: int         # 댓글 수 (performance score 계산용)
    duration_seconds: int
    days_since_upload: int     # 업로드 후 경과 일수 (score 계산용)
    selection_reason: str = "" # "hit" | "low" | "latest"


@dataclass
class VideoAnalysisResult:
    """개별 영상 분석 결과."""
    video_id: str              # YTChannelVideo.id
    video_type: str            # "정보형", "튜토리얼형", "브이로그형", etc.
    content_structure: str     # "문제→해결→요약", "인트로→본론→마무리", etc.
    tone_manner: str           # "차분하고 설명적인", "에너지 넘치는", etc.
    key_topics: List[str]      # 주요 주제 키워드
    summary: str               # 영상 내용 요약 (2-3문장)
    strengths: List[str]       # 강점
    weaknesses: List[str]      # 약점/개선점
    performance_insight: str   # 성과와 연결된 인사이트
    # 댓글 기반 분석 (NEW)
    viewer_reactions: List[str]   # 시청자 반응 (댓글 기반)
    viewer_needs: List[str]       # 시청자 니즈/요청사항
    performance_reason: str       # 이 영상이 hit/low인 이유


@dataclass
class BatchAnalysisOutput:
    """배치 분석 결과 (개별 분석 + 패턴 + 말투 후보)."""
    results: List["VideoAnalysisResult"]  # 개별 영상 분석 결과
    patterns: Optional[List[str]] = None  # 공통 패턴
    tone_candidates: Optional[List[str]] = None  # 말투 샘플 후보 문장


@dataclass
class ChannelVideoSummary:
    """채널 전체 영상 분석 요약."""
    video_types: dict          # {"정보형": 40, "튜토리얼형": 30, ...} (퍼센트)
    content_structures: dict   # {"정보형": "문제→해결→요약", ...}
    tone_manner: str           # 채널 전체 톤앤매너 설명
    tone_samples: List[str]    # 말투 샘플 문장 (few-shot용)
    hit_patterns: List[str]    # ["실용적 팁 제공", "초반 훅 강함"]
    low_patterns: List[str]    # ["주제 모호", "영상 너무 김"]
    success_formula: str       # "실용적 정보를 빠르게 전달"
    # 시청자 반응 분석 (NEW)
    viewer_likes: List[str]         # 시청자가 좋아하는 포인트 (히트 영상 기반)
    viewer_dislikes: List[str]      # 시청자가 싫어하는 포인트 (저조 영상 기반)
    current_viewer_needs: List[str] # 현재 시청자 니즈 (최신 영상 기반)


# ============================================================================
# Performance Score 계산
# ============================================================================

def calculate_performance_score(
    view_count: int,
    like_count: int,
    comment_count: int,
    days_since_upload: int,
) -> float:
    """
    영상 성과 점수 계산.

    공식:
    - View Velocity (60%): view_count / days_since_upload
    - Engagement Rate (40%): (likes + comments×2) / views

    두 지표를 정규화 없이 가중 합산 (상대적 순위만 중요)
    """
    days = max(days_since_upload, 1)  # 0일 방지

    # 1. View Velocity (가중치 0.6)
    velocity = view_count / days

    # 2. Engagement Rate (가중치 0.4)
    if view_count > 0:
        engagement = (like_count + comment_count * 2) / view_count
    else:
        engagement = 0

    # Velocity가 훨씬 큰 값이므로, engagement를 스케일업
    # engagement는 보통 0.01~0.1 범위, velocity는 수천~수만
    # engagement에 velocity 스케일을 곱해서 비슷한 범위로 맞춤
    score = velocity * 0.6 + (engagement * velocity) * 0.4

    return score


# ============================================================================
# 영상 선정
# ============================================================================

async def select_videos_for_analysis(
    db: AsyncSession,
    channel_id: str,
    hit_count: int = 5,
    low_count: int = 5,
    latest_count: int = 5,
) -> List[VideoForAnalysis]:
    """
    분석할 영상 15개 선정.

    Performance Score 기반 선정:
    - 히트 영상: score 상위 5개
    - 저조 영상: score 하위 5개
    - 최신 영상: hit/low 제외 후 최신순 5개

    Score = View Velocity × 0.6 + Engagement Rate × 0.4
    - View Velocity: view_count / days_since_upload
    - Engagement Rate: (likes + comments×2) / views

    Returns:
        List[VideoForAnalysis]: 분석 대상 영상 목록
    """
    # 서브쿼리: 영상별 최신 stats
    latest_stats_subq = (
        select(
            YTVideoStats.video_id,
            func.max(YTVideoStats.date).label("max_date")
        )
        .group_by(YTVideoStats.video_id)
        .subquery()
    )

    # 채널 영상 + 최신 통계 조회 (최신순 정렬 유지)
    stmt = (
        select(YTChannelVideo, YTVideoStats)
        .where(YTChannelVideo.channel_id == channel_id)
        .outerjoin(
            latest_stats_subq,
            latest_stats_subq.c.video_id == YTChannelVideo.id
        )
        .outerjoin(
            YTVideoStats,
            (YTVideoStats.video_id == YTChannelVideo.id) &
            (YTVideoStats.date == latest_stats_subq.c.max_date)
        )
        .order_by(YTChannelVideo.published_at.desc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        logger.warning(f"[VideoAnalyzer] 채널에 영상 없음: {channel_id}")
        return []

    # 방어 코드: 영상 부족 시 분석 중단
    min_required = hit_count + low_count  # 최소 10개 필요
    if len(rows) < min_required:
        logger.warning(
            f"[VideoAnalyzer] 영상 부족으로 분석 중단: "
            f"{len(rows)}개 < 최소 {min_required}개 필요 (채널: {channel_id})"
        )
        return []

    now = datetime.now(timezone.utc)

    # VideoForAnalysis로 변환 (최신순 유지)
    all_videos = []
    for video, stats in rows:
        # 업로드 후 경과 일수 계산
        if video.published_at:
            published = video.published_at
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            days_since = (now - published).days
        else:
            days_since = 30  # 기본값

        view_count = stats.view_count if stats else 0
        like_count = stats.like_count if stats else 0
        comment_count = stats.comment_count if stats else 0

        all_videos.append(VideoForAnalysis(
            id=str(video.id),
            youtube_video_id=video.video_id,
            title=video.title,
            view_count=view_count,
            like_count=like_count,
            comment_count=comment_count,
            duration_seconds=video.duration_seconds or 0,
            days_since_upload=days_since,
            selection_reason="",
        ))

    # Performance Score 계산 및 정렬
    def get_score(v: VideoForAnalysis) -> float:
        return calculate_performance_score(
            view_count=v.view_count,
            like_count=v.like_count,
            comment_count=v.comment_count,
            days_since_upload=v.days_since_upload,
        )

    # Score 기준 정렬
    sorted_by_score = sorted(all_videos, key=get_score, reverse=True)

    # 히트 영상 (score 상위 N개)
    hit_videos = sorted_by_score[:hit_count]
    for v in hit_videos:
        v.selection_reason = "hit"

    # 저조 영상 (score 하위 N개)
    low_videos = sorted_by_score[-low_count:]
    for v in low_videos:
        v.selection_reason = "low"

    # 히트/저조 ID 집합
    selected_ids = {v.id for v in hit_videos + low_videos}

    # 최신 영상: all_videos는 이미 최신순이므로, hit/low 제외 후 앞에서 N개
    latest_candidates = [v for v in all_videos if v.id not in selected_ids]
    latest_videos = latest_candidates[:latest_count]
    for v in latest_videos:
        v.selection_reason = "latest"

    # 합치기
    selected = hit_videos + low_videos + latest_videos

    logger.info(
        f"[VideoAnalyzer] 영상 선정 완료 (Performance Score 기반): "
        f"hit={len(hit_videos)}, low={len(low_videos)}, latest={len(latest_videos)}, "
        f"total={len(selected)}"
    )

    return selected


# ============================================================================
# 자막 추출
# ============================================================================

async def get_transcripts_for_videos(
    videos: List[VideoForAnalysis],
    access_token: Optional[str] = None,
) -> List[Tuple[VideoForAnalysis, str]]:
    """
    영상 목록의 자막을 가져옴.

    Args:
        videos: 분석 대상 영상 목록
        access_token: OAuth 토큰 (있으면 YouTube API 사용, 없으면 yt-dlp)

    Returns:
        List[(video, transcript_text)]: 자막이 있는 영상과 자막 텍스트
    """
    if not videos:
        return []

    videos_with_transcripts = []

    # access_token이 있으면 YouTube Captions API 사용 (본인 채널)
    if access_token:
        logger.info(f"[VideoAnalyzer] YouTube Captions API로 자막 추출 시작 ({len(videos)}개)")

        for video in videos:
            try:
                result = await YouTubeService.fetch_video_captions(
                    video_id=video.youtube_video_id,
                    access_token=access_token,
                    languages=["ko", "en"],
                )

                if result and result.get("status") == "success":
                    tracks = result.get("tracks", [])
                    if tracks:
                        cues = tracks[0].get("cues", [])
                        transcript_text = " ".join(cue.get("text", "") for cue in cues)

                        if transcript_text.strip():
                            videos_with_transcripts.append((video, transcript_text))
                            logger.debug(
                                f"[VideoAnalyzer] 자막 추출 성공 (API): {video.youtube_video_id}, "
                                f"길이={len(transcript_text)}"
                            )
                else:
                    logger.debug(f"[VideoAnalyzer] 자막 없음 (API): {video.youtube_video_id}")

                # Rate limit 방지
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.warning(f"[VideoAnalyzer] 자막 추출 실패 (API): {video.youtube_video_id}, {e}")

    # access_token이 없으면 yt-dlp 사용 (경쟁자 채널 등)
    else:
        logger.info(f"[VideoAnalyzer] yt-dlp로 자막 추출 시작 ({len(videos)}개)")

        video_ids = [v.youtube_video_id for v in videos]

        results = await SubtitleService.fetch_subtitles(
            video_ids=video_ids,
            languages=["ko", "en"],
            db=None,
        )

        result_map = {r["video_id"]: r for r in results}

        for video in videos:
            result = result_map.get(video.youtube_video_id)
            if not result or result.get("status") != "success":
                logger.debug(f"[VideoAnalyzer] 자막 없음 (yt-dlp): {video.youtube_video_id}")
                continue

            tracks = result.get("tracks", [])
            if not tracks:
                continue

            cues = tracks[0].get("cues", [])
            transcript_text = " ".join(cue.get("text", "") for cue in cues)

            if transcript_text.strip():
                videos_with_transcripts.append((video, transcript_text))
                logger.debug(
                    f"[VideoAnalyzer] 자막 추출 성공 (yt-dlp): {video.youtube_video_id}, "
                    f"길이={len(transcript_text)}"
                )

    logger.info(
        f"[VideoAnalyzer] 자막 추출 완료: "
        f"{len(videos_with_transcripts)}/{len(videos)} 성공"
    )

    return videos_with_transcripts


# ============================================================================
# 댓글 추출
# ============================================================================

async def get_comments_for_videos(
    videos: List[VideoForAnalysis],
    max_per_video: int = 10,
) -> dict:
    """
    영상 목록의 댓글을 가져옴 (좋아요 순 상위 N개).

    Args:
        videos: 분석 대상 영상 목록
        max_per_video: 영상당 가져올 댓글 수

    Returns:
        dict: {video.id: [{"text": 댓글내용, "likes": 좋아요수}, ...]}
    """
    if not videos:
        return {}

    api_key = settings.youtube_api_key
    if not api_key:
        logger.warning("[VideoAnalyzer] YouTube API 키 없음, 댓글 수집 스킵")
        return {}

    comments_map = {}

    for video in videos:
        try:
            comments = await _fetch_video_comments(
                video_id=video.youtube_video_id,
                api_key=api_key,
                max_results=max_per_video,
            )
            comments_map[video.id] = comments
            logger.debug(
                f"[VideoAnalyzer] 댓글 추출: {video.youtube_video_id}, "
                f"{len(comments)}개"
            )
        except Exception as e:
            logger.warning(f"[VideoAnalyzer] 댓글 추출 실패 ({video.youtube_video_id}): {e}")
            comments_map[video.id] = []

        # Rate limit 방지
        await asyncio.sleep(0.5)

    success_count = sum(1 for c in comments_map.values() if c)
    logger.info(
        f"[VideoAnalyzer] 댓글 추출 완료: "
        f"{success_count}/{len(videos)} 성공"
    )

    return comments_map


async def _fetch_video_comments(
    video_id: str,
    api_key: str,
    max_results: int = 10,
) -> List[dict]:
    """
    YouTube API로 단일 영상의 댓글 가져오기.

    Args:
        video_id: YouTube 영상 ID
        api_key: YouTube Data API 키
        max_results: 가져올 댓글 수

    Returns:
        List[dict]: [{"text": 댓글내용, "likes": 좋아요수}, ...]
    """
    BASE_URL = "https://www.googleapis.com/youtube/v3"

    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": min(max_results * 2, 100),  # 필터링 위해 더 가져옴
        "order": "relevance",
        "key": api_key,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{BASE_URL}/commentThreads", params=params)

            if resp.status_code == 403:
                # 댓글 비활성화된 영상
                logger.debug(f"[VideoAnalyzer] 댓글 비활성화: {video_id}")
                return []

            if resp.status_code == 404:
                logger.debug(f"[VideoAnalyzer] 영상 없음: {video_id}")
                return []

            if resp.status_code != 200:
                logger.warning(f"[VideoAnalyzer] 댓글 API 에러 {resp.status_code}: {video_id}")
                return []

            data = resp.json()
            items = data.get("items", [])

            comments = []
            for item in items:
                snippet = item.get("snippet", {})
                top_comment = snippet.get("topLevelComment", {})
                comment_snippet = top_comment.get("snippet", {})

                comments.append({
                    "text": comment_snippet.get("textDisplay", ""),
                    "likes": comment_snippet.get("likeCount", 0),
                })

            # 좋아요 순 정렬 후 상위 N개
            comments.sort(key=lambda x: -x["likes"])
            return comments[:max_results]

    except httpx.TimeoutException:
        logger.warning(f"[VideoAnalyzer] 댓글 API 타임아웃: {video_id}")
        return []
    except Exception as e:
        logger.error(f"[VideoAnalyzer] 댓글 API 에러 ({video_id}): {e}")
        return []


# ============================================================================
# LLM 분석
# ============================================================================

async def analyze_videos_batch(
    videos_with_transcripts: List[Tuple[VideoForAnalysis, str]],
    comments_map: Optional[dict] = None,
) -> Tuple[List[VideoAnalysisResult], List[str], List[str], List[str], List[str]]:
    """
    영상들을 배치로 LLM 분석.

    hit/low/latest로 그룹화하여 처리하고,
    각 배치에서 공통 패턴 + 말투 후보 문장 추출.

    Args:
        videos_with_transcripts: (영상, 자막) 튜플 리스트
        comments_map: {video.id: [댓글 리스트]} 딕셔너리 (Optional)

    Returns:
        Tuple[개별 분석 결과, hit 패턴, low 패턴, latest 패턴, tone 후보들]
    """
    if comments_map is None:
        comments_map = {}
    if not videos_with_transcripts:
        return [], [], [], [], []

    api_key = settings.gemini_api_key
    if not api_key:
        logger.error("[VideoAnalyzer] Gemini API 키 없음")
        return [], [], [], [], []

    # selection_reason별로 그룹화
    hit_videos = [(v, t) for v, t in videos_with_transcripts if v.selection_reason == "hit"]
    low_videos = [(v, t) for v, t in videos_with_transcripts if v.selection_reason == "low"]
    latest_videos = [(v, t) for v, t in videos_with_transcripts if v.selection_reason == "latest"]

    logger.info(
        f"[VideoAnalyzer] 그룹화 완료: hit={len(hit_videos)}, "
        f"low={len(low_videos)}, latest={len(latest_videos)}"
    )

    all_results = []
    hit_patterns = []
    low_patterns = []
    latest_patterns = []
    all_tone_candidates = []

    # 1. hit 배치 분석 (개별 분석 + 공통 패턴 + 말투 후보)
    if hit_videos:
        logger.info(f"[VideoAnalyzer] hit 배치 분석 시작 ({len(hit_videos)}개)")
        try:
            output = await _analyze_batch_with_llm(hit_videos, api_key, batch_type="hit", comments_map=comments_map)
            all_results.extend(output.results)
            hit_patterns = output.patterns or []
            if output.tone_candidates:
                all_tone_candidates.extend(output.tone_candidates)
            logger.info(f"[VideoAnalyzer] hit 배치 완료: {len(output.results)}개 결과, 패턴 {len(hit_patterns)}개")
        except Exception as e:
            logger.error(f"[VideoAnalyzer] hit 배치 실패: {e}")

        await asyncio.sleep(10.0)  # Gemini rate limit 방지

    # 2. low 배치 분석 (개별 분석 + 공통 패턴 + 말투 후보)
    if low_videos:
        logger.info(f"[VideoAnalyzer] low 배치 분석 시작 ({len(low_videos)}개)")
        try:
            output = await _analyze_batch_with_llm(low_videos, api_key, batch_type="low", comments_map=comments_map)
            all_results.extend(output.results)
            low_patterns = output.patterns or []
            if output.tone_candidates:
                all_tone_candidates.extend(output.tone_candidates)
            logger.info(f"[VideoAnalyzer] low 배치 완료: {len(output.results)}개 결과, 패턴 {len(low_patterns)}개")
        except Exception as e:
            logger.error(f"[VideoAnalyzer] low 배치 실패: {e}")

        await asyncio.sleep(10.0)  # Gemini rate limit 방지

    # 3. latest 배치 분석 (개별 분석 + 공통 패턴 + 말투 후보)
    if latest_videos:
        logger.info(f"[VideoAnalyzer] latest 배치 분석 시작 ({len(latest_videos)}개)")
        try:
            output = await _analyze_batch_with_llm(latest_videos, api_key, batch_type="latest", comments_map=comments_map)
            all_results.extend(output.results)
            latest_patterns = output.patterns or []
            if output.tone_candidates:
                all_tone_candidates.extend(output.tone_candidates)
            logger.info(f"[VideoAnalyzer] latest 배치 완료: {len(output.results)}개 결과, 패턴 {len(latest_patterns)}개")
        except Exception as e:
            logger.error(f"[VideoAnalyzer] latest 배치 실패: {e}")

    logger.info(f"[VideoAnalyzer] 전체 분석 완료: {len(all_results)}개 결과, tone 후보 {len(all_tone_candidates)}개")
    return all_results, hit_patterns, low_patterns, latest_patterns, all_tone_candidates


async def _analyze_batch_with_llm(
    batch: List[Tuple[VideoForAnalysis, str]],
    api_key: str,
    batch_type: str = "latest",  # "hit" / "low" / "latest"
    max_retries: int = 3,
    comments_map: Optional[dict] = None,
) -> BatchAnalysisOutput:
    """단일 배치를 LLM으로 분석. 429 에러 시 재시도."""
    if comments_map is None:
        comments_map = {}

    # 프롬프트 구성
    videos_text = ""
    for idx, (video, transcript) in enumerate(batch, 1):
        # 댓글 텍스트 구성
        comments = comments_map.get(video.id, [])
        comments_text = ""
        if comments:
            comment_lines = []
            for c in comments[:10]:  # 최대 10개
                likes_str = f"(좋아요 {c['likes']})" if c.get('likes') else ""
                comment_lines.append(f"- {c['text']} {likes_str}")
            comments_text = "\n".join(comment_lines)

        videos_text += f"""
---
### 영상 {idx}
- ID: {video.id}
- 제목: {video.title}
- 조회수: {video.view_count:,}
- 좋아요: {video.like_count:,}
- 길이: {video.duration_seconds // 60}분 {video.duration_seconds % 60}초

자막:
{transcript}

시청자 댓글 (좋아요 순 상위):
{comments_text if comments_text else "(댓글 없음)"}
"""

    # 기본 프롬프트
    if batch_type == "hit":
        batch_desc = "성과가 좋은 히트 영상들 (조회수 속도 + 참여도 기준)"
        pattern_desc = "히트"
    elif batch_type == "low":
        batch_desc = "성과가 저조한 영상들 (조회수 속도 + 참여도 기준)"
        pattern_desc = "저조"
    else:
        batch_desc = "최신 영상들"
        pattern_desc = "최신"

    prompt = f"""다음은 유튜브 채널의 {batch_desc}입니다. 각 영상을 자막과 댓글을 함께 분석해주세요.

{videos_text}

---

다음 JSON 형식으로 응답해주세요:

```json
{{
  "videos": [
    {{
      "video_id": "영상 ID (위에 제공된 ID 그대로)",
      "video_type": "영상 유형 (정보형/튜토리얼형/브이로그형/리뷰형/엔터테인먼트형/인터뷰형/뉴스형 중 하나)",
      "content_structure": "콘텐츠 구조 (예: 문제→해결→요약, 인트로→본론→마무리)",
      "tone_manner": "말투와 분위기 (예: 차분하고 설명적인, 친근하고 유머러스한)",
      "key_topics": ["주요 주제 키워드1", "키워드2", "키워드3"],
      "summary": "영상 내용 2-3문장 요약",
      "strengths": ["강점1", "강점2"],
      "weaknesses": ["개선점1", "개선점2"],
      "performance_insight": "조회수/좋아요와 연결된 성과 인사이트",
      "viewer_reactions": ["댓글에서 드러나는 시청자 반응1", "반응2", "반응3"],
      "viewer_needs": ["시청자가 원하는 것/요청사항1", "요청사항2"],
      "performance_reason": "이 영상이 {pattern_desc}인 이유 (댓글 반응 기반 분석)"
    }}
  ],
  "common_patterns": ["이 {pattern_desc} 영상들의 공통 패턴1", "공통 패턴2", "공통 패턴3"],
  "tone_candidates": [
    "자막에서 발견한 특징적인 말투 예시 문장1 (실제 자막 원문 그대로)",
    "특징적인 말투 예시 문장2",
    "특징적인 말투 예시 문장3"
  ]
}}
```

중요:
- 모든 영상에 대해 분석 결과를 포함해주세요
- video_id는 위에 제공된 ID를 그대로 사용해주세요
- common_patterns에는 이 영상들이 공통으로 가진 특징을 3-5개 추출해주세요
- tone_candidates에는 이 크리에이터의 말투/어투가 잘 드러나는 실제 문장을 5-7개 추출해주세요
  - 문장 종결 패턴 (예: ~거든요, ~하시죠)
  - 자주 쓰는 표현 (예: 자, 사실, 근데)
  - 인사말, 마무리 멘트 등
- viewer_reactions, viewer_needs는 댓글 내용을 분석하여 작성해주세요
  - 댓글이 없으면 자막 내용에서 예상되는 시청자 반응을 추론해주세요
- performance_reason은 "{pattern_desc}" 영상인 이유를 댓글 반응 기반으로 분석해주세요
"""

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 0.3,
                            "maxOutputTokens": 16384,
                            "responseMimeType": "application/json",
                        },
                    },
                )

                if resp.status_code == 429:
                    wait_time = (attempt + 1) * 5  # 5초, 10초, 15초
                    logger.warning(f"[VideoAnalyzer] 429 에러, {wait_time}초 대기 후 재시도 ({attempt+1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue

                if resp.status_code != 200:
                    logger.error(f"[VideoAnalyzer] LLM API 에러: {resp.status_code}")
                    return BatchAnalysisOutput(results=[], patterns=None)

                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    logger.error("[VideoAnalyzer] LLM 응답에 candidates 없음")
                    return BatchAnalysisOutput(results=[], patterns=None)

                text = candidates[0]["content"]["parts"][0]["text"]

                # JSON 파싱
                text = text.strip()
                text = re.sub(r'^```json\s*', '', text)
                text = re.sub(r'^```\s*', '', text)
                text = re.sub(r'\s*```$', '', text)

                response_data = json.loads(text)

                # JSON 구조: {"videos": [...], "common_patterns": [...], "tone_candidates": [...]}
                videos_data = response_data.get("videos", [])
                common_patterns = response_data.get("common_patterns", None)
                tone_candidates = response_data.get("tone_candidates", None)

                # VideoAnalysisResult로 변환
                results = []
                for item in videos_data:
                    results.append(VideoAnalysisResult(
                        video_id=item.get("video_id", ""),
                        video_type=item.get("video_type", ""),
                        content_structure=item.get("content_structure", ""),
                        tone_manner=item.get("tone_manner", ""),
                        key_topics=item.get("key_topics", []),
                        summary=item.get("summary", ""),
                        strengths=item.get("strengths", []),
                        weaknesses=item.get("weaknesses", []),
                        performance_insight=item.get("performance_insight", ""),
                        # 댓글 기반 분석 (NEW)
                        viewer_reactions=item.get("viewer_reactions", []),
                        viewer_needs=item.get("viewer_needs", []),
                        performance_reason=item.get("performance_reason", ""),
                    ))

                return BatchAnalysisOutput(
                    results=results,
                    patterns=common_patterns,
                    tone_candidates=tone_candidates,
                )

        except (json.JSONDecodeError, Exception) as e:
            error_type = "JSON 파싱 실패" if isinstance(e, json.JSONDecodeError) else "LLM 분석 실패"
            logger.error(f"[VideoAnalyzer] {error_type}: {e}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                logger.warning(f"[VideoAnalyzer] {wait_time}초 대기 후 재시도")
                await asyncio.sleep(wait_time)
            else:
                return BatchAnalysisOutput(results=[], patterns=None, tone_candidates=None)

    logger.error(f"[VideoAnalyzer] {max_retries}번 시도 후 실패")
    return BatchAnalysisOutput(results=[], patterns=None, tone_candidates=None)


async def analyze_hit_vs_low_comparison(
    hit_patterns: List[str],
    low_patterns: List[str],
    latest_patterns: List[str],
    tone_candidates: List[str],
    hit_viewer_data: Optional[List[dict]] = None,
    low_viewer_data: Optional[List[dict]] = None,
    latest_viewer_data: Optional[List[dict]] = None,
    max_retries: int = 3,
) -> dict:
    """
    패턴 비교 분석 + 말투 종합 + 시청자 반응 분석.

    Args:
        hit_patterns: 히트 영상 공통 패턴 리스트
        low_patterns: 저조 영상 공통 패턴 리스트
        latest_patterns: 최신 영상 공통 패턴 리스트
        tone_candidates: 말투 샘플 후보 문장들
        hit_viewer_data: 히트 영상들의 시청자 반응 [{reactions: [], needs: []}, ...]
        low_viewer_data: 저조 영상들의 시청자 반응
        latest_viewer_data: 최신 영상들의 시청자 반응

    Returns:
        dict: {
            tone_manner, tone_samples, success_formula,
            viewer_likes, viewer_dislikes, current_viewer_needs
        }
    """
    if hit_viewer_data is None:
        hit_viewer_data = []
    if low_viewer_data is None:
        low_viewer_data = []
    if latest_viewer_data is None:
        latest_viewer_data = []
    api_key = settings.gemini_api_key
    if not api_key:
        logger.error("[VideoAnalyzer] Gemini API 키 없음")
        return {"tone_manner": "", "tone_samples": [], "success_formula": "", "viewer_likes": [], "viewer_dislikes": [], "current_viewer_needs": []}

    if not hit_patterns and not low_patterns and not tone_candidates:
        logger.warning("[VideoAnalyzer] 비교 분석할 데이터 없음")
        return {"tone_manner": "", "tone_samples": [], "success_formula": "", "viewer_likes": [], "viewer_dislikes": [], "current_viewer_needs": []}

    hit_text = "\n".join(f"- {p}" for p in hit_patterns) if hit_patterns else "- 분석 결과 없음"
    low_text = "\n".join(f"- {p}" for p in low_patterns) if low_patterns else "- 분석 결과 없음"
    latest_text = "\n".join(f"- {p}" for p in latest_patterns) if latest_patterns else "- 분석 결과 없음"
    tone_text = "\n".join(f"- {t}" for t in tone_candidates) if tone_candidates else "- 샘플 없음"

    # 시청자 반응 데이터 텍스트 구성
    def format_viewer_data(data_list: List[dict]) -> str:
        if not data_list:
            return "- 데이터 없음"
        lines = []
        for item in data_list:
            reactions = item.get("reactions", [])
            needs = item.get("needs", [])
            if reactions:
                lines.append(f"  반응: {', '.join(reactions[:3])}")
            if needs:
                lines.append(f"  니즈: {', '.join(needs[:2])}")
        return "\n".join(lines) if lines else "- 데이터 없음"

    hit_viewer_text = format_viewer_data(hit_viewer_data)
    low_viewer_text = format_viewer_data(low_viewer_data)
    latest_viewer_text = format_viewer_data(latest_viewer_data)

    prompt = f"""다음은 한 유튜브 채널의 영상 분석 결과입니다.

## 히트 영상들의 공통 패턴 (조회수 높음)
{hit_text}

### 히트 영상 시청자 반응 (댓글 기반)
{hit_viewer_text}

## 저조 영상들의 공통 패턴 (조회수 낮음)
{low_text}

### 저조 영상 시청자 반응 (댓글 기반)
{low_viewer_text}

## 최신 영상들의 공통 패턴
{latest_text}

### 최신 영상 시청자 반응 (댓글 기반) ★ 현재 시청자 니즈 파악에 중요
{latest_viewer_text}

## 크리에이터의 말투 샘플 후보
{tone_text}

---

위 내용을 종합 분석하여 다음 JSON 형식으로 응답해주세요:

```json
{{
  "success_formula": "이 채널에서 성공하는 영상의 공식을 1-2문장으로 요약",
  "tone_manner": "이 크리에이터의 말투 특성을 상세히 설명 (문장 종결 패턴, 자주 쓰는 표현, 전체적인 톤 등)",
  "tone_samples": [
    "이 크리에이터의 말투가 가장 잘 드러나는 대표 문장1",
    "대표 문장2",
    "대표 문장3",
    "대표 문장4",
    "대표 문장5"
  ],
  "viewer_likes": ["시청자가 좋아하는 포인트1 (히트 영상 댓글 기반)", "포인트2", "포인트3"],
  "viewer_dislikes": ["시청자가 싫어하는/부족하다고 느끼는 포인트1 (저조 영상 댓글 기반)", "포인트2"],
  "current_viewer_needs": ["최근 시청자가 원하는 것1 (최신 영상 댓글 기반, 가중치 높음)", "원하는 것2", "원하는 것3"]
}}
```

중요:
- success_formula: 히트 vs 저조 비교를 통해 구체적이고 실행 가능한 성공 공식 도출
- tone_manner: 스크립트 작성 시 참고할 수 있도록 말투 특성을 상세히 설명
- tone_samples: 위 후보 중에서 말투가 가장 잘 드러나는 5-7개 문장 선별
- viewer_likes: 히트 영상 댓글에서 발견된 시청자가 좋아하는 공통 포인트 3-5개
- viewer_dislikes: 저조 영상 댓글에서 발견된 시청자가 싫어하거나 부족하다고 느끼는 포인트 2-4개
- current_viewer_needs: 최신 영상 댓글을 중심으로 현재 시청자가 원하는 것 3-5개 (가장 중요!)
"""

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 0.3,
                            "maxOutputTokens": 2048,
                            "responseMimeType": "application/json",
                        },
                    },
                )

                if resp.status_code == 429:
                    wait_time = (attempt + 1) * 5  # 5초, 10초, 15초
                    logger.warning(f"[VideoAnalyzer] 비교 분석 429 에러, {wait_time}초 대기 후 재시도 ({attempt+1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue

                if resp.status_code != 200:
                    logger.error(f"[VideoAnalyzer] 비교 분석 API 에러: {resp.status_code}")
                    return {"tone_manner": "", "tone_samples": [], "success_formula": "", "viewer_likes": [], "viewer_dislikes": [], "current_viewer_needs": []}

                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    logger.error("[VideoAnalyzer] 비교 분석 응답에 candidates 없음")
                    return {"tone_manner": "", "tone_samples": [], "success_formula": "", "viewer_likes": [], "viewer_dislikes": [], "current_viewer_needs": []}

                text = candidates[0]["content"]["parts"][0]["text"]

                # JSON 파싱
                text = text.strip()
                text = re.sub(r'^```json\s*', '', text)
                text = re.sub(r'^```\s*', '', text)
                text = re.sub(r'\s*```$', '', text)

                response_data = json.loads(text)

                success_formula = response_data.get("success_formula", "")
                tone_manner = response_data.get("tone_manner", "")
                tone_samples = response_data.get("tone_samples", [])
                # 시청자 분석 (NEW)
                viewer_likes = response_data.get("viewer_likes", [])
                viewer_dislikes = response_data.get("viewer_dislikes", [])
                current_viewer_needs = response_data.get("current_viewer_needs", [])

                logger.info(
                    f"[VideoAnalyzer] 비교 분석 완료: "
                    f"성공공식 있음={bool(success_formula)}, "
                    f"tone_manner 있음={bool(tone_manner)}, "
                    f"tone_samples={len(tone_samples)}개, "
                    f"viewer_likes={len(viewer_likes)}개, "
                    f"viewer_dislikes={len(viewer_dislikes)}개, "
                    f"current_needs={len(current_viewer_needs)}개"
                )

                return {
                    "tone_manner": tone_manner,
                    "tone_samples": tone_samples,
                    "success_formula": success_formula,
                    "viewer_likes": viewer_likes,
                    "viewer_dislikes": viewer_dislikes,
                    "current_viewer_needs": current_viewer_needs,
                }

        except (json.JSONDecodeError, Exception) as e:
            error_type = "JSON 파싱 실패" if isinstance(e, json.JSONDecodeError) else "분석 실패"
            logger.error(f"[VideoAnalyzer] 비교 분석 {error_type}: {e}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                logger.warning(f"[VideoAnalyzer] 비교 분석 {wait_time}초 대기 후 재시도")
                await asyncio.sleep(wait_time)
            else:
                return {"tone_manner": "", "tone_samples": [], "success_formula": "", "viewer_likes": [], "viewer_dislikes": [], "current_viewer_needs": []}

    logger.error(f"[VideoAnalyzer] 비교 분석 {max_retries}번 시도 후 실패")
    return {"tone_manner": "", "tone_samples": [], "success_formula": "", "viewer_likes": [], "viewer_dislikes": [], "current_viewer_needs": []}


# ============================================================================
# 결과 저장
# ============================================================================

async def save_analysis_results(
    db: AsyncSession,
    channel_id: str,
    videos: List[VideoForAnalysis],
    results: List[VideoAnalysisResult],
    transcripts: dict,  # video_id (str) → transcript
) -> None:
    """
    분석 결과를 DB에 저장.

    N+1 문제 해결: 기존 레코드를 한 번에 조회 (15번 → 1번 쿼리)
    """
    import uuid as uuid_module

    # video_id → result 매핑
    result_map = {r.video_id: r for r in results}

    # video_id → VideoForAnalysis 매핑
    video_map = {v.id: v for v in videos}

    # string → UUID 변환 (유효한 것만)
    video_id_uuids = []
    video_id_str_to_uuid = {}
    for video_id_str in result_map.keys():
        try:
            video_id_uuid = uuid_module.UUID(video_id_str)
            video_id_uuids.append(video_id_uuid)
            video_id_str_to_uuid[video_id_str] = video_id_uuid
        except ValueError:
            logger.warning(f"[VideoAnalyzer] 잘못된 video_id: {video_id_str}")

    # 기존 레코드 한 번에 조회 (N+1 → 1번 쿼리)
    existing_map = {}
    if video_id_uuids:
        stmt = select(YTMyVideoAnalysis).where(
            YTMyVideoAnalysis.video_id.in_(video_id_uuids)
        )
        existing_results = await db.execute(stmt)
        for record in existing_results.scalars().all():
            existing_map[str(record.video_id)] = record

    saved_count = 0
    for video_id_str, result in result_map.items():
        video = video_map.get(video_id_str)
        if not video:
            continue

        video_id_uuid = video_id_str_to_uuid.get(video_id_str)
        if not video_id_uuid:
            continue

        transcript = transcripts.get(video_id_str, "")

        # 기존 레코드 확인 (이미 조회한 맵에서 가져옴)
        existing = existing_map.get(video_id_str)

        if existing:
            # 업데이트
            existing.video_type = result.video_type
            existing.content_structure = result.content_structure
            existing.tone_manner = result.tone_manner
            existing.key_topics = result.key_topics
            existing.summary = result.summary
            existing.strengths = result.strengths
            existing.weaknesses = result.weaknesses
            existing.performance_insight = result.performance_insight
            existing.viewer_reactions = result.viewer_reactions
            existing.viewer_needs = result.viewer_needs
            existing.performance_reason = result.performance_reason
            existing.transcript_text = transcript
        else:
            # 새로 생성
            analysis = YTMyVideoAnalysis(
                channel_id=channel_id,
                video_id=video_id_uuid,
                video_type=result.video_type,
                content_structure=result.content_structure,
                tone_manner=result.tone_manner,
                key_topics=result.key_topics,
                summary=result.summary,
                strengths=result.strengths,
                weaknesses=result.weaknesses,
                performance_insight=result.performance_insight,
                viewer_reactions=result.viewer_reactions,
                viewer_needs=result.viewer_needs,
                performance_reason=result.performance_reason,
                transcript_text=transcript,
                selection_reason=video.selection_reason,
            )
            db.add(analysis)

        saved_count += 1

    await db.commit()
    logger.info(f"[VideoAnalyzer] DB 저장 완료: {saved_count}개")


# ============================================================================
# 채널 전체 요약
# ============================================================================

def summarize_video_analyses(
    results: List[VideoAnalysisResult],
    hit_patterns: List[str],
    low_patterns: List[str],
    tone_manner: str,
    tone_samples: List[str],
    success_formula: str,
    viewer_likes: Optional[List[str]] = None,
    viewer_dislikes: Optional[List[str]] = None,
    current_viewer_needs: Optional[List[str]] = None,
) -> ChannelVideoSummary:
    """
    개별 영상 분석 결과를 채널 단위로 집계.

    Args:
        results: 개별 영상 분석 결과
        hit_patterns: 히트 영상 공통 패턴
        low_patterns: 저조 영상 공통 패턴
        tone_manner: 말투 특성 설명
        tone_samples: 말투 샘플 문장
        success_formula: 성공 공식
        viewer_likes: 시청자가 좋아하는 포인트
        viewer_dislikes: 시청자가 싫어하는 포인트
        current_viewer_needs: 현재 시청자 니즈

    Returns:
        ChannelVideoSummary: 채널 전체 요약
    """
    if not results:
        return ChannelVideoSummary(
            video_types={},
            content_structures={},
            tone_manner=tone_manner or "분석 필요",
            tone_samples=tone_samples or [],
            hit_patterns=hit_patterns or [],
            low_patterns=low_patterns or [],
            success_formula=success_formula or "",
            viewer_likes=viewer_likes or [],
            viewer_dislikes=viewer_dislikes or [],
            current_viewer_needs=current_viewer_needs or [],
        )

    # 영상 유형 집계
    type_counts = {}
    for r in results:
        vtype = r.video_type
        type_counts[vtype] = type_counts.get(vtype, 0) + 1

    total = len(results)
    video_types = {
        vtype: round(count / total * 100)
        for vtype, count in type_counts.items()
    }

    # 유형별 대표 구조
    content_structures = {}
    for vtype in type_counts.keys():
        # 해당 유형의 영상들의 구조 중 가장 흔한 것
        structures = [r.content_structure for r in results if r.video_type == vtype]
        if structures:
            # 가장 흔한 구조 선택 (간단히 첫 번째 사용)
            content_structures[vtype] = structures[0]

    return ChannelVideoSummary(
        video_types=video_types,
        content_structures=content_structures,
        tone_manner=tone_manner or "분석 필요",
        tone_samples=tone_samples or [],
        hit_patterns=hit_patterns or [],
        low_patterns=low_patterns or [],
        success_formula=success_formula or "",
        viewer_likes=viewer_likes or [],
        viewer_dislikes=viewer_dislikes or [],
        current_viewer_needs=current_viewer_needs or [],
    )


# ============================================================================
# 메인 오케스트레이터
# ============================================================================

async def analyze_channel_videos(
    db: AsyncSession,
    channel_id: str,
    min_videos_required: int = 8,
    access_token: Optional[str] = None,
) -> Optional[ChannelVideoSummary]:
    """
    채널 영상 분석 파이프라인.

    1. 영상 15개 선정
    2. 자막 추출 (access_token 있으면 YouTube API, 없으면 yt-dlp)
    3. LLM 분석 (5개씩 배치)
    4. DB 저장
    5. 채널 요약 생성

    Args:
        db: DB 세션
        channel_id: 채널 ID
        min_videos_required: 최소 필요 영상 수 (자막 있는 것 기준)
        access_token: OAuth 토큰 (본인 채널이면 전달)

    Returns:
        ChannelVideoSummary or None
    """
    logger.info(f"[VideoAnalyzer] 채널 영상 분석 시작: {channel_id}")

    # 1. 영상 선정
    videos = await select_videos_for_analysis(db, channel_id)
    if not videos:
        logger.warning(f"[VideoAnalyzer] 분석할 영상 없음: {channel_id}")
        return None

    # 2. 자막 추출 (access_token 있으면 YouTube API 사용)
    videos_with_transcripts = await get_transcripts_for_videos(videos, access_token=access_token)

    if len(videos_with_transcripts) < min_videos_required:
        logger.warning(
            f"[VideoAnalyzer] 자막 있는 영상 부족: "
            f"{len(videos_with_transcripts)} < {min_videos_required}"
        )
        return None

    # transcript 맵 만들기
    transcripts = {v.id: t for v, t in videos_with_transcripts}

    # 2.5. 댓글 추출
    videos_for_comments = [v for v, _ in videos_with_transcripts]
    comments_map = await get_comments_for_videos(videos_for_comments, max_per_video=10)

    # 3. LLM 분석 (hit/low/latest 그룹별로 분석 + 패턴 + tone 후보 추출)
    results, hit_patterns, low_patterns, latest_patterns, tone_candidates = await analyze_videos_batch(
        videos_with_transcripts,
        comments_map=comments_map,
    )

    if not results:
        logger.warning(f"[VideoAnalyzer] LLM 분석 결과 없음: {channel_id}")
        return None

    # 3.5. 개별 분석 결과에서 시청자 데이터 추출 (hit/low/latest별)
    videos_map = {v.id: v for v, _ in videos_with_transcripts}
    hit_viewer_data = []
    low_viewer_data = []
    latest_viewer_data = []

    for r in results:
        video = videos_map.get(r.video_id)
        if not video:
            continue
        viewer_item = {
            "reactions": r.viewer_reactions,
            "needs": r.viewer_needs,
        }
        if video.selection_reason == "hit":
            hit_viewer_data.append(viewer_item)
        elif video.selection_reason == "low":
            low_viewer_data.append(viewer_item)
        else:  # latest
            latest_viewer_data.append(viewer_item)

    # 4. 비교 분석 (success_formula + tone_manner + tone_samples + 시청자 분석)
    await asyncio.sleep(10.0)  # Gemini rate limit 방지
    comparison_result = await analyze_hit_vs_low_comparison(
        hit_patterns=hit_patterns,
        low_patterns=low_patterns,
        latest_patterns=latest_patterns,
        tone_candidates=tone_candidates,
        hit_viewer_data=hit_viewer_data,
        low_viewer_data=low_viewer_data,
        latest_viewer_data=latest_viewer_data,
    )

    tone_manner = comparison_result.get("tone_manner", "")
    tone_samples = comparison_result.get("tone_samples", [])
    success_formula = comparison_result.get("success_formula", "")
    viewer_likes = comparison_result.get("viewer_likes", [])
    viewer_dislikes = comparison_result.get("viewer_dislikes", [])
    current_viewer_needs = comparison_result.get("current_viewer_needs", [])

    logger.info(
        f"[VideoAnalyzer] 비교 분석 완료: "
        f"hit_patterns={len(hit_patterns)}, low_patterns={len(low_patterns)}, "
        f"tone_samples={len(tone_samples)}개, success_formula 있음={bool(success_formula)}, "
        f"viewer_likes={len(viewer_likes)}개, current_needs={len(current_viewer_needs)}개"
    )

    # 5. DB 저장
    await save_analysis_results(
        db=db,
        channel_id=channel_id,
        videos=videos,
        results=results,
        transcripts=transcripts,
    )

    # 6. 채널 요약 생성
    summary = summarize_video_analyses(
        results=results,
        hit_patterns=hit_patterns,
        low_patterns=low_patterns,
        tone_manner=tone_manner,
        tone_samples=tone_samples,
        success_formula=success_formula,
        viewer_likes=viewer_likes,
        viewer_dislikes=viewer_dislikes,
        current_viewer_needs=current_viewer_needs,
    )

    logger.info(
        f"[VideoAnalyzer] 채널 영상 분석 완료: {channel_id}, "
        f"분석된 영상={len(results)}, "
        f"유형={summary.video_types}, "
        f"tone_samples={len(summary.tone_samples)}개"
    )

    return summary
