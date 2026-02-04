"""
채널 페르소나 종합 서비스

규칙 기반 해석 + LLM 해석을 종합하여 최종 페르소나를 생성합니다.
"""
from typing import List, Optional
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.channel_persona import ChannelPersona
from app.models.channel_video import YTChannelVideo, YTVideoStats
from app.services.persona_analyzer import (
    analyze_channel_tier,
    analyze_audience,
    analyze_view_consistency,
    analyze_engagement,
    AudienceData,
    GeoData,
    VideoStatsData,
)
from app.services.persona_llm_analyzer import (
    analyze_video_titles,
    analyze_hit_vs_low,
    analyze_channel_description,
    VideoInfo,
)


async def generate_persona(
    db: AsyncSession,
    channel_id: str,
) -> Optional[ChannelPersona]:
    """
    채널 페르소나 생성 파이프라인.

    1. 채널 정보 조회
    2. 영상 데이터 조회
    3. 규칙 기반 해석 (4개)
    4. LLM 해석 (3개)
    5. 종합 페르소나 생성
    6. DB 저장

    Args:
        db: 데이터베이스 세션
        channel_id: YouTube 채널 ID

    Returns:
        ChannelPersona or None
    """
    # 1. 채널 정보 조회
    from app.models.youtube_channel import YouTubeChannel
    stmt = select(YouTubeChannel).where(YouTubeChannel.channel_id == channel_id)
    result = await db.execute(stmt)
    channel = result.scalar_one_or_none()

    if not channel:
        print(f"Channel not found: {channel_id}")
        return None

    # 2. 영상 데이터 조회
    videos = await _get_channel_videos_with_stats(db, channel_id)

    # 3. 시청자 데이터 조회 (있는 경우)
    audience_data = await _get_audience_data(db, channel_id)
    geo_data = await _get_geo_data(db, channel_id)

    # 3.5. 채널 통계에서 구독자 수 조회
    subscriber_count = await _get_subscriber_count(db, channel_id)

    # 4. 규칙 기반 해석
    rule_interpretations = _run_rule_interpretations(
        subscriber_count=subscriber_count,
        audience_data=audience_data,
        geo_data=geo_data,
        video_stats=videos,
    )

    # 5. LLM 해석
    llm_interpretations = await _run_llm_interpretations(
        videos=videos,
        channel_description=channel.description or "",
        channel_title=channel.title or "",
    )

    # 6. 종합 페르소나 생성
    persona_data = await _synthesize_persona(
        channel=channel,
        rule_interpretations=rule_interpretations,
        llm_interpretations=llm_interpretations,
    )

    # 7. DB 저장 (upsert)
    persona = await _save_persona(db, channel_id, persona_data)

    return persona


async def _get_channel_videos_with_stats(
    db: AsyncSession,
    channel_id: str,
) -> List[VideoStatsData]:
    """채널 영상과 통계를 조회하여 VideoStatsData 목록으로 변환."""
    stmt = (
        select(YTChannelVideo)
        .where(YTChannelVideo.channel_id == channel_id)
        .order_by(YTChannelVideo.published_at.desc())
        .limit(50)
    )
    result = await db.execute(stmt)
    videos = list(result.scalars().all())

    video_stats_list = []
    for video in videos:
        # 가장 최근 통계 가져오기
        stats_stmt = (
            select(YTVideoStats)
            .where(YTVideoStats.video_id == video.id)
            .order_by(YTVideoStats.date.desc())
            .limit(1)
        )
        stats_result = await db.execute(stats_stmt)
        stats = stats_result.scalar_one_or_none()

        video_stats_list.append(VideoStatsData(
            video_id=str(video.id),
            title=video.title,
            view_count=stats.view_count if stats else 0,
            like_count=stats.like_count if stats else 0,
            comment_count=stats.comment_count if stats else 0,
        ))

    return video_stats_list


async def _get_subscriber_count(
    db: AsyncSession,
    channel_id: str,
) -> int:
    """채널 통계에서 최신 구독자 수 조회."""
    try:
        from app.models.youtube_channel import YTChannelStatsDaily
        stmt = (
            select(YTChannelStatsDaily)
            .where(YTChannelStatsDaily.channel_id == channel_id)
            .order_by(YTChannelStatsDaily.date.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        stats = result.scalar_one_or_none()

        if stats and stats.subscriber_count:
            return stats.subscriber_count
        return 0
    except Exception:
        return 0


async def _get_audience_data(
    db: AsyncSession,
    channel_id: str,
) -> List[AudienceData]:
    """시청자 인구통계 데이터 조회."""
    try:
        from app.models.yt_audience_daily import YTAudienceDaily
        stmt = (
            select(YTAudienceDaily)
            .where(YTAudienceDaily.channel_id == channel_id)
            .order_by(YTAudienceDaily.date.desc())
            .limit(7)  # 최근 7일
        )
        result = await db.execute(stmt)
        records = list(result.scalars().all())

        return [
            AudienceData(
                age_group=r.age_group,
                gender=r.gender,
                percentage=r.viewer_percentage or 0,
            )
            for r in records
        ]
    except Exception:
        return []


async def _get_geo_data(
    db: AsyncSession,
    channel_id: str,
) -> List[GeoData]:
    """지역별 시청자 데이터 조회."""
    try:
        from app.models.yt_geo_daily import YTGeoDaily
        stmt = (
            select(YTGeoDaily)
            .where(YTGeoDaily.channel_id == channel_id)
            .order_by(YTGeoDaily.date.desc())
            .limit(10)
        )
        result = await db.execute(stmt)
        records = list(result.scalars().all())

        return [
            GeoData(
                country=r.country,
                percentage=r.viewer_percentage or 0,
            )
            for r in records
        ]
    except Exception:
        return []


def _run_rule_interpretations(
    subscriber_count: int,
    audience_data: List[AudienceData],
    geo_data: List[GeoData],
    video_stats: List[VideoStatsData],
) -> dict:
    """규칙 기반 해석 실행."""
    return {
        "channel_tier": asdict(analyze_channel_tier(subscriber_count)),
        "audience": asdict(analyze_audience(audience_data, geo_data)),
        "view_consistency": asdict(analyze_view_consistency(video_stats)),
        "engagement": asdict(analyze_engagement(video_stats)),
    }


async def _run_llm_interpretations(
    videos: List[VideoStatsData],
    channel_description: str,
    channel_title: str,
) -> dict:
    """LLM 해석 실행."""
    # 제목 목록 추출
    titles = [v.title for v in videos]

    # 히트/저조 영상 분리
    sorted_videos = sorted(videos, key=lambda v: v.view_count, reverse=True)
    hit_count = max(1, len(sorted_videos) // 10)  # 상위 10%
    low_count = max(1, len(sorted_videos) // 5)   # 하위 20%

    hit_videos = [
        VideoInfo(title=v.title, view_count=v.view_count, like_count=v.like_count)
        for v in sorted_videos[:hit_count]
    ]
    low_videos = [
        VideoInfo(title=v.title, view_count=v.view_count, like_count=v.like_count)
        for v in sorted_videos[-low_count:]
    ]

    # LLM 해석 실행
    title_result = await analyze_video_titles(titles)
    hit_low_result = await analyze_hit_vs_low(hit_videos, low_videos)
    desc_result = await analyze_channel_description(channel_description, channel_title)

    return {
        "title_analysis": asdict(title_result) if title_result else None,
        "hit_vs_low": asdict(hit_low_result) if hit_low_result else None,
        "description_analysis": asdict(desc_result) if desc_result else None,
    }


async def _synthesize_persona(
    channel,
    rule_interpretations: dict,
    llm_interpretations: dict,
) -> dict:
    """
    모든 해석을 종합하여 최종 페르소나 데이터 생성.

    LLM을 사용하여 자연스러운 요약을 생성합니다.
    """
    import httpx
    import json
    import re

    api_key = settings.gemini_api_key

    # 해석 결과를 텍스트로 정리
    context = _format_interpretations_for_llm(
        channel_title=channel.title or "",
        rule_interpretations=rule_interpretations,
        llm_interpretations=llm_interpretations,
    )

    # LLM으로 종합 페르소나 생성
    prompt = f"""다음은 유튜브 채널 분석 결과입니다. 이를 종합하여 채널 페르소나를 JSON으로 생성해주세요.

채널명: {channel.title or "알 수 없음"}

분석 결과:
{context}

다음 JSON 형식으로 응답해주세요. 반드시 유효한 JSON만 출력하세요:
{{
    "persona_summary": "이 채널에 대한 자연스러운 3~5문장 요약",
    "one_liner": "한 줄 정의",
    "main_topics": ["주요 주제1", "주요 주제2", "주요 주제3"],
    "content_style": "콘텐츠 스타일",
    "differentiator": "차별화 포인트",
    "target_audience": "타겟 시청자",
    "audience_needs": "시청자가 원하는 것",
    "hit_topics": ["잘 되는 주제1", "잘 되는 주제2"],
    "title_patterns": ["제목 패턴1", "패턴2"],
    "optimal_duration": "적정 영상 길이",
    "growth_opportunities": ["성장 기회1", "성장 기회2"],
    "topic_keywords": ["키워드1", "키워드2", "키워드3"],
    "style_keywords": ["스타일키워드1", "스타일키워드2"],
    "analyzed_categories": ["카테고리1", "카테고리2"],
    "analyzed_subcategories": ["세부카테고리1", "세부카테고리2"]
}}"""

    if not api_key:
        print("[Persona Synthesis] No Gemini API key, using default persona")
        return _build_default_persona(
            channel, rule_interpretations, llm_interpretations
        )

    MAX_RETRIES = 2
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 0.7,
                            "maxOutputTokens": 8192,
                            "responseMimeType": "application/json",
                        },
                    },
                )

                if resp.status_code != 200:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    print(f"[Persona Synthesis] Attempt {attempt+1} failed: {last_error}")
                    continue

                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    last_error = f"No candidates in response: {data}"
                    print(f"[Persona Synthesis] Attempt {attempt+1}: {last_error}")
                    continue

                text = candidates[0]["content"]["parts"][0]["text"]

                # JSON 추출 (responseMimeType 사용 시 보통 깨끗한 JSON이 옴)
                text = text.strip()

                # 혹시 마크다운 코드블록으로 감싸져 있으면 제거
                text = re.sub(r'^```json\s*', '', text)
                text = re.sub(r'^```\s*', '', text)
                text = re.sub(r'\s*```$', '', text)

                # trailing comma 제거
                text = re.sub(r',\s*}', '}', text)
                text = re.sub(r',\s*]', ']', text)

                persona_data = json.loads(text.strip())

                # evidence 추가
                persona_data["evidence"] = _build_evidence(
                    rule_interpretations, llm_interpretations
                )

                print(f"[Persona Synthesis] Success on attempt {attempt+1}")
                return persona_data

        except json.JSONDecodeError as e:
            last_error = f"JSON parse error: {e}"
            print(f"[Persona Synthesis] Attempt {attempt+1} JSON parse failed: {e}")
            # 다음 시도에서 재시도
        except Exception as e:
            last_error = f"Unexpected error: {e}"
            print(f"[Persona Synthesis] Attempt {attempt+1} error: {e}")

    # 모든 시도 실패
    print(f"[Persona Synthesis] All {MAX_RETRIES} attempts failed. Last error: {last_error}")
    print("[Persona Synthesis] Falling back to default persona")
    return _build_default_persona(
        channel, rule_interpretations, llm_interpretations
    )


def _format_interpretations_for_llm(
    channel_title: str,
    rule_interpretations: dict,
    llm_interpretations: dict,
) -> str:
    """해석 결과를 LLM이 이해하기 쉬운 텍스트로 변환."""
    lines = []

    # 규칙 기반 해석
    lines.append("### 규칙 기반 분석")

    tier = rule_interpretations.get("channel_tier", {})
    lines.append(f"- 채널 규모: {tier.get('signal', '')} → {tier.get('interpretation', '')}")

    audience = rule_interpretations.get("audience", {})
    lines.append(f"- 시청자층: {audience.get('signal', '')} → {audience.get('interpretation', '')}")

    consistency = rule_interpretations.get("view_consistency", {})
    lines.append(f"- 조회수 일관성: {consistency.get('signal', '')} → {consistency.get('interpretation', '')}")

    engagement = rule_interpretations.get("engagement", {})
    lines.append(f"- 참여도: {engagement.get('signal', '')} → {engagement.get('interpretation', '')}")

    # LLM 해석
    lines.append("\n### LLM 기반 분석")

    title_analysis = llm_interpretations.get("title_analysis")
    if title_analysis:
        lines.append(f"- 주요 주제: {', '.join(title_analysis.get('content_topics', []))}")
        lines.append(f"- 제목 스타일: {title_analysis.get('title_style', '')}")
        lines.append(f"- 콘텐츠 성격: {title_analysis.get('interpretation', '')}")

    hit_vs_low = llm_interpretations.get("hit_vs_low")
    if hit_vs_low:
        lines.append(f"- 히트 요인: {', '.join(hit_vs_low.get('hit_factors', []))}")
        lines.append(f"- 성공 공식: {hit_vs_low.get('success_formula', '')}")

    desc_analysis = llm_interpretations.get("description_analysis")
    if desc_analysis:
        lines.append(f"- 채널 정체성: {desc_analysis.get('channel_identity', '')}")
        lines.append(f"- 브랜딩 수준: {desc_analysis.get('professionalism', '')}")

    return "\n".join(lines)


def _build_evidence(
    rule_interpretations: dict,
    llm_interpretations: dict,
) -> list:
    """해석 결과를 evidence 목록으로 변환."""
    evidence = []

    for key, interp in rule_interpretations.items():
        evidence.append({
            "source": f"rule:{key}",
            "signal": interp.get("signal", ""),
            "interpretation": interp.get("interpretation", ""),
            "category": interp.get("category", ""),
            "confidence": interp.get("confidence", "medium"),
        })

    for key, interp in llm_interpretations.items():
        if interp:
            evidence.append({
                "source": f"llm:{key}",
                "data": interp,
            })

    return evidence


def _build_default_persona(
    channel,
    rule_interpretations: dict,
    llm_interpretations: dict,
) -> dict:
    """LLM 실패 시 기본 페르소나 생성."""
    title_analysis = llm_interpretations.get("title_analysis") or {}

    return {
        "persona_summary": f"{channel.title or '이 채널'}에 대한 분석이 완료되었습니다. LLM 종합이 필요합니다.",
        "one_liner": channel.title or "알 수 없음",
        "main_topics": title_analysis.get("content_topics", []),
        "content_style": title_analysis.get("title_style", "분석 필요"),
        "differentiator": "분석 필요",
        "target_audience": rule_interpretations.get("audience", {}).get("interpretation", "분석 필요"),
        "audience_needs": "분석 필요",
        "hit_topics": [],
        "title_patterns": title_analysis.get("title_patterns", []),
        "optimal_duration": "분석 필요",
        "growth_opportunities": [],
        "topic_keywords": title_analysis.get("content_topics", []),
        "style_keywords": [],
        "evidence": _build_evidence(rule_interpretations, llm_interpretations),
    }


async def _save_persona(
    db: AsyncSession,
    channel_id: str,
    persona_data: dict,
) -> ChannelPersona:
    """페르소나를 DB에 저장 (upsert). Race condition 처리 포함."""
    from sqlalchemy.exc import IntegrityError

    stmt = select(ChannelPersona).where(ChannelPersona.channel_id == channel_id)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        # 업데이트
        for key, value in persona_data.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
        persona = existing
    else:
        # 새로 생성 시도
        try:
            persona = ChannelPersona(
                channel_id=channel_id,
                **persona_data,
            )
            db.add(persona)
            await db.commit()
            await db.refresh(persona)
            return persona
        except IntegrityError:
            # Race condition: 다른 요청이 먼저 생성함 → rollback 후 업데이트
            await db.rollback()
            stmt = select(ChannelPersona).where(ChannelPersona.channel_id == channel_id)
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                for key, value in persona_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                persona = existing
            else:
                raise  # 정말 예상치 못한 상황

    await db.commit()
    await db.refresh(persona)

    return persona


async def get_persona(
    db: AsyncSession,
    channel_id: str,
) -> Optional[ChannelPersona]:
    """채널 페르소나 조회."""
    stmt = select(ChannelPersona).where(ChannelPersona.channel_id == channel_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_persona(
    db: AsyncSession,
    channel_id: str,
    update_data: dict,
) -> Optional[ChannelPersona]:
    """페르소나 수동 수정."""
    stmt = select(ChannelPersona).where(ChannelPersona.channel_id == channel_id)
    result = await db.execute(stmt)
    persona = result.scalar_one_or_none()

    if not persona:
        return None

    for key, value in update_data.items():
        if hasattr(persona, key) and key not in ("id", "channel_id", "created_at"):
            setattr(persona, key, value)

    await db.commit()
    await db.refresh(persona)

    return persona
