"""
채널 페르소나 종합 서비스

규칙 기반 해석 + 자막 분석을 종합하여 최종 페르소나를 생성합니다.
"""
import asyncio
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
    analyze_optimal_duration,
    AudienceData,
    GeoData,
    VideoStatsData,
)
from app.services.video_analyzer import analyze_channel_videos, ChannelVideoSummary


async def generate_persona(
    db: AsyncSession,
    channel_id: str,
) -> Optional[ChannelPersona]:
    """
    채널 페르소나 생성 파이프라인.

    1. 채널 정보 조회
    2. 영상 데이터 조회
    3. 규칙 기반 해석 (5개)
    4. 영상 자막 분석 (15개, 최소 8개 필수) - LLM 4번
    5. 종합 페르소나 생성 (자막 분석 결과 포함) - LLM 1번
    6. DB 저장

    총 LLM 호출: 5번 (기존 7번에서 2번 감소)

    Args:
        db: 데이터베이스 세션
        channel_id: YouTube 채널 ID

    Returns:
        ChannelPersona or None
    """
    print(f"\n{'='*60}")
    print(f"[Persona] 페르소나 생성 시작: {channel_id}")
    print(f"{'='*60}")

    # 1. 채널 정보 조회
    print(f"[Persona] 1단계: 채널 정보 조회...")
    from app.models.youtube_channel import YouTubeChannel
    from app.models.oauth import OAuthAccount
    stmt = select(YouTubeChannel).where(YouTubeChannel.channel_id == channel_id)
    result = await db.execute(stmt)
    channel = result.scalar_one_or_none()

    if not channel:
        print(f"[Persona] ❌ 1단계 실패: 채널을 찾을 수 없음 ({channel_id})")
        return None
    print(f"[Persona] ✓ 1단계 완료: {channel.title}")

    # 1.5. 사용자의 OAuth 토큰 조회 (본인 채널 자막용)
    access_token = None
    if channel.user_id:
        oauth_stmt = select(OAuthAccount).where(OAuthAccount.user_id == channel.user_id)
        oauth_result = await db.execute(oauth_stmt)
        oauth_account = oauth_result.scalar_one_or_none()
        if oauth_account and oauth_account.access_token:
            access_token = oauth_account.access_token
            print(f"[Persona]   └─ OAuth 토큰 발견 → YouTube API로 자막 추출")

    # 2. 영상 데이터 조회
    print(f"[Persona] 2단계: 영상 데이터 조회...")
    try:
        videos = await _get_channel_videos_with_stats(db, channel_id)
        print(f"[Persona] ✓ 2단계 완료: 영상 {len(videos)}개 조회")
    except Exception as e:
        print(f"[Persona] ❌ 2단계 실패: 영상 데이터 조회 오류 - {e}")
        videos = []

    # 3. 시청자 데이터 조회 (있는 경우)
    print(f"[Persona] 3단계: 시청자/구독자 데이터 조회...")
    audience_data = await _get_audience_data(db, channel_id)
    geo_data = await _get_geo_data(db, channel_id)
    subscriber_count = await _get_subscriber_count(db, channel_id)
    print(f"[Persona] ✓ 3단계 완료: 구독자 {subscriber_count:,}명, 시청자 데이터 {len(audience_data)}개")

    # 4. 규칙 기반 해석
    print(f"[Persona] 4단계: 규칙 기반 해석 (5개)...")
    rule_interpretations = _run_rule_interpretations(
        subscriber_count=subscriber_count,
        audience_data=audience_data,
        geo_data=geo_data,
        video_stats=videos,
    )
    print(f"[Persona] ✓ 4단계 완료: 채널 티어, 시청자층, 조회수 일관성, 참여도, 적정 길이 분석")

    # 5. 영상 자막 분석 (15개 영상, 5개씩 배치) - LLM 4번
    print(f"[Persona] 5단계: 영상 자막 분석 (LLM 4번 호출)...")
    video_analysis_summary = None
    try:
        video_analysis_summary = await analyze_channel_videos(
            db=db,
            channel_id=channel_id,
            min_videos_required=8,
            access_token=access_token,
        )
        if video_analysis_summary:
            print(f"[Persona] ✓ 5단계 완료: 영상 유형={video_analysis_summary.video_types}")
        else:
            print(f"[Persona] ⚠ 5단계: 자막 분석 결과 없음 (자막 부족)")
    except Exception as e:
        print(f"[Persona] ❌ 5단계 실패: 자막 분석 오류 - {e}")

    # 6. 종합 페르소나 생성 (자막 분석 결과 + 채널 설명 포함) - LLM 1번
    print(f"[Persona] 6단계: 종합 페르소나 생성 (LLM 1번 호출)...")
    try:
        persona_data = await _synthesize_persona(
            channel=channel,
            rule_interpretations=rule_interpretations,
            video_analysis_summary=video_analysis_summary,
        )
        print(f"[Persona] ✓ 6단계 완료: {persona_data.get('one_liner', '페르소나 생성됨')}")
    except Exception as e:
        print(f"[Persona] ❌ 6단계 실패: 종합 페르소나 생성 오류 - {e}")
        raise

    # 7. DB 저장 (upsert)
    print(f"[Persona] 7단계: DB 저장...")
    try:
        persona = await _save_persona(db, channel_id, persona_data)
        print(f"[Persona] ✓ 7단계 완료: DB 저장 성공")
    except Exception as e:
        print(f"[Persona] ❌ 7단계 실패: DB 저장 오류 - {e}")
        raise

    print(f"{'='*60}")
    print(f"[Persona] 페르소나 생성 완료: {channel.title}")
    print(f"{'='*60}\n")

    return persona


async def _get_channel_videos_with_stats(
    db: AsyncSession,
    channel_id: str,
) -> List[VideoStatsData]:
    """
    채널 영상과 통계를 조회하여 VideoStatsData 목록으로 변환.

    N+1 문제 해결: 서브쿼리 + LEFT JOIN으로 1번 쿼리로 처리.
    (기존: 51번 쿼리 → 변경: 1번 쿼리)
    """
    from sqlalchemy import func, and_

    # 서브쿼리: 영상별 최신 stats 날짜
    latest_stats_subq = (
        select(
            YTVideoStats.video_id,
            func.max(YTVideoStats.date).label("max_date")
        )
        .group_by(YTVideoStats.video_id)
        .subquery()
    )

    # 메인 쿼리: 영상 + 최신 stats 한 번에 조회
    stmt = (
        select(YTChannelVideo, YTVideoStats)
        .where(YTChannelVideo.channel_id == channel_id)
        .outerjoin(
            latest_stats_subq,
            latest_stats_subq.c.video_id == YTChannelVideo.id
        )
        .outerjoin(
            YTVideoStats,
            and_(
                YTVideoStats.video_id == YTChannelVideo.id,
                YTVideoStats.date == latest_stats_subq.c.max_date
            )
        )
        .order_by(YTChannelVideo.published_at.desc())
        .limit(50)
    )

    result = await db.execute(stmt)
    rows = result.all()

    video_stats_list = []
    for video, stats in rows:
        video_stats_list.append(VideoStatsData(
            video_id=str(video.id),
            title=video.title,
            view_count=stats.view_count if stats else 0,
            like_count=stats.like_count if stats else 0,
            comment_count=stats.comment_count if stats else 0,
            duration_seconds=video.duration_seconds or 0,
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
        "optimal_duration": asdict(analyze_optimal_duration(video_stats)),
    }


async def _synthesize_persona(
    channel,
    rule_interpretations: dict,
    video_analysis_summary: Optional[ChannelVideoSummary],
) -> dict:
    """
    모든 해석을 종합하여 최종 페르소나 데이터 생성.

    규칙 기반 해석 + 자막 분석 결과 + 채널 설명을 종합합니다.
    """
    import httpx
    import json
    import re

    api_key = settings.gemini_api_key

    # 해석 결과를 텍스트로 정리
    context = _format_interpretations_for_llm(
        channel=channel,
        rule_interpretations=rule_interpretations,
        video_analysis_summary=video_analysis_summary,
    )

    # LLM으로 종합 페르소나 생성
    prompt = f"""다음은 유튜브 채널 분석 결과입니다. 이를 종합하여 채널 페르소나를 JSON으로 생성해주세요.

채널명: {channel.title or "알 수 없음"}

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
        return _build_default_persona(channel, rule_interpretations, video_analysis_summary)

    MAX_RETRIES = 3
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

                if resp.status_code == 429:
                    wait_time = (attempt + 1) * 5  # 5초, 10초, 15초
                    last_error = f"HTTP 429: Rate limit"
                    print(f"[Persona Synthesis] 429 에러, {wait_time}초 대기 후 재시도 ({attempt+1}/{MAX_RETRIES})")
                    await asyncio.sleep(wait_time)
                    continue

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
                persona_data["evidence"] = _build_evidence(rule_interpretations)

                # 자막 분석 결과 직접 추가 (LLM이 생성한 게 아니라 자막 분석에서 나온 것)
                if video_analysis_summary:
                    persona_data["video_types"] = video_analysis_summary.video_types
                    persona_data["content_structures"] = video_analysis_summary.content_structures
                    persona_data["tone_manner"] = video_analysis_summary.tone_manner
                    persona_data["tone_samples"] = video_analysis_summary.tone_samples
                    persona_data["hit_patterns"] = video_analysis_summary.hit_patterns
                    persona_data["low_patterns"] = video_analysis_summary.low_patterns
                    persona_data["success_formula"] = video_analysis_summary.success_formula
                    persona_data["viewer_likes"] = video_analysis_summary.viewer_likes
                    persona_data["viewer_dislikes"] = video_analysis_summary.viewer_dislikes
                    persona_data["current_viewer_needs"] = video_analysis_summary.current_viewer_needs

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
    return _build_default_persona(channel, rule_interpretations, video_analysis_summary)


def _format_interpretations_for_llm(
    channel,
    rule_interpretations: dict,
    video_analysis_summary: Optional[ChannelVideoSummary],
) -> str:
    """해석 결과를 LLM이 이해하기 쉬운 텍스트로 변환."""
    lines = []

    # 채널 설명 (직접 텍스트로)
    if channel.description and len(channel.description.strip()) > 10:
        lines.append("### 채널 설명")
        lines.append(channel.description.strip())
        lines.append("")

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

    optimal_duration = rule_interpretations.get("optimal_duration", {})
    lines.append(f"- 적정 영상 길이: {optimal_duration.get('signal', '')} → {optimal_duration.get('interpretation', '')}")

    # 자막 분석 결과
    if video_analysis_summary:
        lines.append("\n### 영상 자막 분석 결과")

        # 영상 유형 분포
        if video_analysis_summary.video_types:
            types_str = ", ".join(f"{k}: {v}%" for k, v in video_analysis_summary.video_types.items())
            lines.append(f"- 영상 유형: {types_str}")

        # 성공 공식
        if video_analysis_summary.success_formula:
            lines.append(f"- 성공 공식: {video_analysis_summary.success_formula}")

        # 히트/저조 패턴
        if video_analysis_summary.hit_patterns:
            lines.append(f"- 히트 영상 패턴: {', '.join(video_analysis_summary.hit_patterns)}")
        if video_analysis_summary.low_patterns:
            lines.append(f"- 저조 영상 패턴: {', '.join(video_analysis_summary.low_patterns)}")

        # 시청자 반응 (댓글 기반)
        if video_analysis_summary.viewer_likes:
            lines.append(f"- 시청자가 좋아하는 것: {', '.join(video_analysis_summary.viewer_likes)}")
        if video_analysis_summary.viewer_dislikes:
            lines.append(f"- 시청자가 싫어하는 것: {', '.join(video_analysis_summary.viewer_dislikes)}")
        if video_analysis_summary.current_viewer_needs:
            lines.append(f"- 현재 시청자 니즈: {', '.join(video_analysis_summary.current_viewer_needs)}")

        # 톤앤매너
        if video_analysis_summary.tone_manner:
            lines.append(f"- 톤앤매너: {video_analysis_summary.tone_manner}")

    return "\n".join(lines)


def _build_evidence(rule_interpretations: dict) -> list:
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

    return evidence


def _build_default_persona(
    channel,
    rule_interpretations: dict,
    video_analysis_summary: Optional[ChannelVideoSummary],
) -> dict:
    """LLM 실패 시 기본 페르소나 생성."""
    optimal_duration = rule_interpretations.get("optimal_duration", {})

    persona = {
        "persona_summary": f"{channel.title or '이 채널'}에 대한 분석이 완료되었습니다. LLM 종합이 필요합니다.",
        "one_liner": channel.title or "알 수 없음",
        "main_topics": [],
        "content_style": "분석 필요",
        "differentiator": "분석 필요",
        "target_audience": rule_interpretations.get("audience", {}).get("interpretation", "분석 필요"),
        "audience_needs": "분석 필요",
        "hit_topics": [],
        "title_patterns": [],
        "optimal_duration": optimal_duration.get("interpretation", "분석 필요"),
        "growth_opportunities": [],
        "topic_keywords": [],
        "style_keywords": [],
        "analyzed_categories": [],
        "analyzed_subcategories": [],
        "evidence": _build_evidence(rule_interpretations),
    }

    # 자막 분석 결과가 있으면 추가
    if video_analysis_summary:
        persona["video_types"] = video_analysis_summary.video_types
        persona["content_structures"] = video_analysis_summary.content_structures
        persona["tone_manner"] = video_analysis_summary.tone_manner
        persona["tone_samples"] = video_analysis_summary.tone_samples
        persona["hit_patterns"] = video_analysis_summary.hit_patterns
        persona["low_patterns"] = video_analysis_summary.low_patterns
        persona["success_formula"] = video_analysis_summary.success_formula
        persona["viewer_likes"] = video_analysis_summary.viewer_likes
        persona["viewer_dislikes"] = video_analysis_summary.viewer_dislikes
        persona["current_viewer_needs"] = video_analysis_summary.current_viewer_needs

    return persona


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
