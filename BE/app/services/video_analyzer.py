"""
영상 자막 기반 분석 서비스

채널 영상의 자막을 분석하여 영상 유형, 콘텐츠 구조, 톤앤매너 등을 추출합니다.
페르소나 고도화에 사용됩니다.
"""
import logging
from dataclasses import dataclass
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
    duration_seconds: int
    selection_reason: str      # "hit" | "low" | "latest"


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


# ============================================================================
# 영상 선정
# ============================================================================

async def select_videos_for_analysis(
    db: AsyncSession,
    channel_id: str,
    hit_count: int = 10,
    low_count: int = 10,
    latest_count: int = 10,
) -> List[VideoForAnalysis]:
    """
    분석할 영상 30개 선정.

    - 히트 영상: 조회수 상위 10개
    - 저조 영상: 조회수 하위 10개
    - 최신 영상: 최근 업로드 10개 (히트/저조와 중복 제외)

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

    # 채널 영상 + 최신 통계 조회
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

    # VideoForAnalysis로 변환
    all_videos = []
    for video, stats in rows:
        all_videos.append(VideoForAnalysis(
            id=str(video.id),
            youtube_video_id=video.video_id,
            title=video.title,
            view_count=stats.view_count if stats else 0,
            like_count=stats.like_count if stats else 0,
            duration_seconds=video.duration_seconds or 0,
            selection_reason="",  # 나중에 설정
        ))

    # 조회수 기준 정렬
    sorted_by_views = sorted(all_videos, key=lambda v: v.view_count, reverse=True)

    # 히트 영상 (상위 N개)
    hit_videos = sorted_by_views[:hit_count]
    for v in hit_videos:
        v.selection_reason = "hit"

    # 저조 영상 (하위 N개)
    low_videos = sorted_by_views[-low_count:]
    for v in low_videos:
        v.selection_reason = "low"

    # 히트/저조 ID 집합
    selected_ids = {v.id for v in hit_videos + low_videos}

    # 최신 영상 (중복 제외)
    latest_candidates = [v for v in all_videos if v.id not in selected_ids]
    latest_videos = latest_candidates[:latest_count]
    for v in latest_videos:
        v.selection_reason = "latest"

    # 합치기
    selected = hit_videos + low_videos + latest_videos

    logger.info(
        f"[VideoAnalyzer] 영상 선정 완료: "
        f"hit={len(hit_videos)}, low={len(low_videos)}, latest={len(latest_videos)}, "
        f"total={len(selected)}"
    )

    return selected


# ============================================================================
# 자막 추출
# ============================================================================

async def get_transcripts_for_videos(
    videos: List[VideoForAnalysis],
) -> List[Tuple[VideoForAnalysis, str]]:
    """
    영상 목록의 자막을 가져옴.

    Args:
        videos: 분석 대상 영상 목록

    Returns:
        List[(video, transcript_text)]: 자막이 있는 영상과 자막 텍스트
    """
    if not videos:
        return []

    video_ids = [v.youtube_video_id for v in videos]

    # SubtitleService로 자막 가져오기
    results = await SubtitleService.fetch_subtitles(
        video_ids=video_ids,
        languages=["ko", "en"],  # 한국어 우선, 영어 폴백
        db=None,  # DB 저장은 나중에 별도로
    )

    # video_id → result 매핑
    result_map = {r["video_id"]: r for r in results}

    # 자막 텍스트 추출
    videos_with_transcripts = []
    for video in videos:
        result = result_map.get(video.youtube_video_id)
        if not result or result.get("status") != "success":
            logger.debug(f"[VideoAnalyzer] 자막 없음: {video.youtube_video_id}")
            continue

        # cues에서 텍스트만 추출
        tracks = result.get("tracks", [])
        if not tracks:
            continue

        cues = tracks[0].get("cues", [])
        transcript_text = " ".join(cue.get("text", "") for cue in cues)

        if transcript_text.strip():
            videos_with_transcripts.append((video, transcript_text))
            logger.debug(
                f"[VideoAnalyzer] 자막 추출 성공: {video.youtube_video_id}, "
                f"길이={len(transcript_text)}"
            )

    logger.info(
        f"[VideoAnalyzer] 자막 추출 완료: "
        f"{len(videos_with_transcripts)}/{len(videos)} 성공"
    )

    return videos_with_transcripts


# ============================================================================
# LLM 분석
# ============================================================================

async def analyze_videos_batch(
    videos_with_transcripts: List[Tuple[VideoForAnalysis, str]],
) -> Tuple[List[VideoAnalysisResult], List[str], List[str], List[str], List[str]]:
    """
    영상들을 배치로 LLM 분석.

    hit/low/latest로 그룹화하여 처리하고,
    각 배치에서 공통 패턴 + 말투 후보 문장 추출.

    Args:
        videos_with_transcripts: (영상, 자막) 튜플 리스트

    Returns:
        Tuple[개별 분석 결과, hit 패턴, low 패턴, latest 패턴, tone 후보들]
    """
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
            output = await _analyze_batch_with_llm(hit_videos, api_key, batch_type="hit")
            all_results.extend(output.results)
            hit_patterns = output.patterns or []
            if output.tone_candidates:
                all_tone_candidates.extend(output.tone_candidates)
            logger.info(f"[VideoAnalyzer] hit 배치 완료: {len(output.results)}개 결과, 패턴 {len(hit_patterns)}개")
        except Exception as e:
            logger.error(f"[VideoAnalyzer] hit 배치 실패: {e}")

        await asyncio.sleep(3.0)

    # 2. low 배치 분석 (개별 분석 + 공통 패턴 + 말투 후보)
    if low_videos:
        logger.info(f"[VideoAnalyzer] low 배치 분석 시작 ({len(low_videos)}개)")
        try:
            output = await _analyze_batch_with_llm(low_videos, api_key, batch_type="low")
            all_results.extend(output.results)
            low_patterns = output.patterns or []
            if output.tone_candidates:
                all_tone_candidates.extend(output.tone_candidates)
            logger.info(f"[VideoAnalyzer] low 배치 완료: {len(output.results)}개 결과, 패턴 {len(low_patterns)}개")
        except Exception as e:
            logger.error(f"[VideoAnalyzer] low 배치 실패: {e}")

        await asyncio.sleep(3.0)

    # 3. latest 배치 분석 (개별 분석 + 공통 패턴 + 말투 후보)
    if latest_videos:
        logger.info(f"[VideoAnalyzer] latest 배치 분석 시작 ({len(latest_videos)}개)")
        try:
            output = await _analyze_batch_with_llm(latest_videos, api_key, batch_type="latest")
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
) -> BatchAnalysisOutput:
    """단일 배치를 LLM으로 분석. 429 에러 시 재시도."""

    # 프롬프트 구성
    videos_text = ""
    for idx, (video, transcript) in enumerate(batch, 1):
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
"""

    # 기본 프롬프트
    if batch_type == "hit":
        batch_desc = "조회수가 높은 히트 영상들"
        pattern_desc = "히트"
    elif batch_type == "low":
        batch_desc = "조회수가 낮은 저조 영상들"
        pattern_desc = "저조"
    else:
        batch_desc = "최신 영상들"
        pattern_desc = "최신"

    prompt = f"""다음은 유튜브 채널의 {batch_desc}입니다. 각 영상을 분석해주세요.

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
      "performance_insight": "조회수/좋아요와 연결된 성과 인사이트"
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
                            "maxOutputTokens": 8192,
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
                    ))

                return BatchAnalysisOutput(
                    results=results,
                    patterns=common_patterns,
                    tone_candidates=tone_candidates,
                )

        except json.JSONDecodeError as e:
            logger.error(f"[VideoAnalyzer] JSON 파싱 실패: {e}")
            return BatchAnalysisOutput(results=[], patterns=None, tone_candidates=None)
        except Exception as e:
            logger.error(f"[VideoAnalyzer] LLM 분석 실패: {e}")
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
    max_retries: int = 3,
) -> Tuple[str, List[str], str]:
    """
    패턴 비교 분석 + 말투 종합.

    Args:
        hit_patterns: 히트 영상 공통 패턴 리스트
        low_patterns: 저조 영상 공통 패턴 리스트
        latest_patterns: 최신 영상 공통 패턴 리스트
        tone_candidates: 말투 샘플 후보 문장들

    Returns:
        Tuple[tone_manner 설명, tone_samples, success_formula]
    """
    api_key = settings.gemini_api_key
    if not api_key:
        logger.error("[VideoAnalyzer] Gemini API 키 없음")
        return "", [], ""

    if not hit_patterns and not low_patterns and not tone_candidates:
        logger.warning("[VideoAnalyzer] 비교 분석할 데이터 없음")
        return "", [], ""

    hit_text = "\n".join(f"- {p}" for p in hit_patterns) if hit_patterns else "- 분석 결과 없음"
    low_text = "\n".join(f"- {p}" for p in low_patterns) if low_patterns else "- 분석 결과 없음"
    latest_text = "\n".join(f"- {p}" for p in latest_patterns) if latest_patterns else "- 분석 결과 없음"
    tone_text = "\n".join(f"- {t}" for t in tone_candidates) if tone_candidates else "- 샘플 없음"

    prompt = f"""다음은 한 유튜브 채널의 영상 분석 결과입니다.

## 히트 영상들의 공통 패턴 (조회수 높음)
{hit_text}

## 저조 영상들의 공통 패턴 (조회수 낮음)
{low_text}

## 최신 영상들의 공통 패턴
{latest_text}

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
  ]
}}
```

중요:
- success_formula: 히트 vs 저조 비교를 통해 구체적이고 실행 가능한 성공 공식 도출
- tone_manner: 스크립트 작성 시 참고할 수 있도록 말투 특성을 상세히 설명 (예: "~거든요 체를 주로 사용하며, '자'로 문장을 시작하는 경우가 많음. 친근하지만 전문적인 느낌")
- tone_samples: 위 후보 중에서 말투가 가장 잘 드러나는 5-7개 문장 선별 (실제 스크립트 생성 시 few-shot 예시로 활용)
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
                    return "", [], ""

                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    logger.error("[VideoAnalyzer] 비교 분석 응답에 candidates 없음")
                    return "", [], ""

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

                logger.info(
                    f"[VideoAnalyzer] 비교 분석 완료: "
                    f"성공공식 있음={bool(success_formula)}, "
                    f"tone_manner 있음={bool(tone_manner)}, "
                    f"tone_samples={len(tone_samples)}개"
                )

                return tone_manner, tone_samples, success_formula

        except json.JSONDecodeError as e:
            logger.error(f"[VideoAnalyzer] 비교 분석 JSON 파싱 실패: {e}")
            return "", [], ""
        except Exception as e:
            logger.error(f"[VideoAnalyzer] 비교 분석 실패: {e}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                logger.warning(f"[VideoAnalyzer] 비교 분석 {wait_time}초 대기 후 재시도")
                await asyncio.sleep(wait_time)
            else:
                return "", [], ""

    logger.error(f"[VideoAnalyzer] 비교 분석 {max_retries}번 시도 후 실패")
    return "", [], ""


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
    """분석 결과를 DB에 저장."""
    import uuid as uuid_module

    # video_id → result 매핑
    result_map = {r.video_id: r for r in results}

    # video_id → VideoForAnalysis 매핑
    video_map = {v.id: v for v in videos}

    saved_count = 0
    for video_id_str, result in result_map.items():
        video = video_map.get(video_id_str)
        if not video:
            continue

        transcript = transcripts.get(video_id_str, "")

        # string → UUID 변환
        try:
            video_id_uuid = uuid_module.UUID(video_id_str)
        except ValueError:
            logger.warning(f"[VideoAnalyzer] 잘못된 video_id: {video_id_str}")
            continue

        # 기존 레코드 확인
        stmt = select(YTMyVideoAnalysis).where(
            YTMyVideoAnalysis.video_id == video_id_uuid
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()

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
    )


# ============================================================================
# 메인 오케스트레이터
# ============================================================================

async def analyze_channel_videos(
    db: AsyncSession,
    channel_id: str,
    min_videos_required: int = 15,
) -> Optional[ChannelVideoSummary]:
    """
    채널 영상 분석 파이프라인.

    1. 영상 30개 선정
    2. 자막 추출
    3. LLM 분석 (10개씩 배치)
    4. DB 저장
    5. 채널 요약 생성

    Args:
        db: DB 세션
        channel_id: 채널 ID
        min_videos_required: 최소 필요 영상 수 (자막 있는 것 기준)

    Returns:
        ChannelVideoSummary or None
    """
    logger.info(f"[VideoAnalyzer] 채널 영상 분석 시작: {channel_id}")

    # 1. 영상 선정
    videos = await select_videos_for_analysis(db, channel_id)
    if not videos:
        logger.warning(f"[VideoAnalyzer] 분석할 영상 없음: {channel_id}")
        return None

    # 2. 자막 추출
    videos_with_transcripts = await get_transcripts_for_videos(videos)

    if len(videos_with_transcripts) < min_videos_required:
        logger.warning(
            f"[VideoAnalyzer] 자막 있는 영상 부족: "
            f"{len(videos_with_transcripts)} < {min_videos_required}"
        )
        return None

    # transcript 맵 만들기
    transcripts = {v.id: t for v, t in videos_with_transcripts}

    # 3. LLM 분석 (hit/low/latest 그룹별로 분석 + 패턴 + tone 후보 추출)
    results, hit_patterns, low_patterns, latest_patterns, tone_candidates = await analyze_videos_batch(videos_with_transcripts)

    if not results:
        logger.warning(f"[VideoAnalyzer] LLM 분석 결과 없음: {channel_id}")
        return None

    # 4. 비교 분석 (success_formula + tone_manner + tone_samples 추출)
    await asyncio.sleep(3.0)  # 배치 분석 후 딜레이
    tone_manner, tone_samples, success_formula = await analyze_hit_vs_low_comparison(
        hit_patterns=hit_patterns,
        low_patterns=low_patterns,
        latest_patterns=latest_patterns,
        tone_candidates=tone_candidates,
    )

    logger.info(
        f"[VideoAnalyzer] 비교 분석 완료: "
        f"hit_patterns={len(hit_patterns)}, low_patterns={len(low_patterns)}, "
        f"tone_samples={len(tone_samples)}개, success_formula 있음={bool(success_formula)}"
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
    )

    logger.info(
        f"[VideoAnalyzer] 채널 영상 분석 완료: {channel_id}, "
        f"분석된 영상={len(results)}, "
        f"유형={summary.video_types}, "
        f"tone_samples={len(summary.tone_samples)}개"
    )

    return summary
