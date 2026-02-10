"""
콘텐츠 주제 추천 서비스

채널 맞춤 추천(주간)과 트렌드 기반 추천(일간)을 생성하고 관리합니다.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_topic import ChannelTopic, TrendTopic
from app.models.channel_persona import ChannelPersona


# =============================================================================
# 조회 서비스
# =============================================================================

async def get_shown_topics(
    db: AsyncSession,
    channel_id: str,
) -> Tuple[List[ChannelTopic], List[TrendTopic]]:
    """
    표시 중인 추천 주제 조회 (채널 맞춤 + 트렌드).

    Returns:
        (channel_topics, trend_topics) - shown 상태인 주제들
    """
    # 채널 맞춤 추천 (shown, 만료 안 됨)
    channel_stmt = select(ChannelTopic).where(
        and_(
            ChannelTopic.channel_id == channel_id,
            ChannelTopic.display_status == "shown",
            ChannelTopic.expires_at > datetime.utcnow(),
        )
    ).order_by(ChannelTopic.rank)

    channel_result = await db.execute(channel_stmt)
    channel_topics = list(channel_result.scalars().all())

    # 트렌드 추천 (shown, 만료 안 됨)
    trend_stmt = select(TrendTopic).where(
        and_(
            TrendTopic.channel_id == channel_id,
            TrendTopic.display_status == "shown",
            TrendTopic.expires_at > datetime.utcnow(),
        )
    ).order_by(TrendTopic.rank)

    trend_result = await db.execute(trend_stmt)
    trend_topics = list(trend_result.scalars().all())

    return channel_topics, trend_topics


async def get_topic_by_id(
    db: AsyncSession,
    topic_id: str,
    topic_type: str,
) -> Optional[ChannelTopic | TrendTopic]:
    """
    ID로 주제 조회.

    Args:
        topic_id: 주제 UUID
        topic_type: "channel" 또는 "trend"
    """
    model = ChannelTopic if topic_type == "channel" else TrendTopic
    stmt = select(model).where(model.id == topic_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def check_recommendations_exist(
    db: AsyncSession,
    channel_id: str,
) -> dict:
    """
    추천 존재 여부 및 만료 상태 확인.

    Returns:
        {
            "channel_exists": bool,
            "channel_expired": bool,
            "trend_exists": bool,
            "trend_expired": bool,
        }
    """
    now = datetime.utcnow()

    # 채널 맞춤 확인
    channel_stmt = select(ChannelTopic).where(
        ChannelTopic.channel_id == channel_id
    ).limit(1)
    channel_result = await db.execute(channel_stmt)
    channel_topic = channel_result.scalar_one_or_none()

    # 트렌드 확인
    trend_stmt = select(TrendTopic).where(
        TrendTopic.channel_id == channel_id
    ).limit(1)
    trend_result = await db.execute(trend_stmt)
    trend_topic = trend_result.scalar_one_or_none()

    # 경쟁자 분석 추천 확인
    competitor_stmt = select(ChannelTopic).where(
        and_(
            ChannelTopic.channel_id == channel_id,
            ChannelTopic.based_on_topic.like("competitor_analysis%"),
        )
    ).limit(1)
    competitor_result = await db.execute(competitor_stmt)
    competitor_topic = competitor_result.scalar_one_or_none()

    return {
        "channel_exists": channel_topic is not None,
        "channel_expired": channel_topic.expires_at < now if channel_topic else True,
        "trend_exists": trend_topic is not None,
        "trend_expired": trend_topic.expires_at < now if trend_topic else True,
        "competitor_exists": competitor_topic is not None,
        "competitor_expired": competitor_topic.expires_at < now if competitor_topic else True,
    }


# =============================================================================
# 생성 서비스
# =============================================================================

async def generate_channel_topics(
    db: AsyncSession,
    channel_id: str,
    count: int = 10,
    shown_count: int = 5,
) -> List[ChannelTopic]:
    """
    채널 맞춤 추천 생성 (주간).

    1. 기존 추천 삭제 (만료됐거나 새로 생성)
    2. Gemini로 추천 생성
    3. DB에 개별 Row로 저장
    4. shown 상태인 것만 반환
    """
    # 1. 페르소나 조회
    persona = await _get_persona(db, channel_id)
    if not persona:
        return []

    # 2. 기존 추천 삭제
    await _delete_existing_topics(db, channel_id, ChannelTopic)

    # 3. Gemini 호출
    recommendations_raw = await _call_topic_rec(persona, count)

    if not recommendations_raw:
        return []

    # 4. DB 저장
    now = datetime.utcnow()
    expires_at = now + timedelta(days=7)  # 주간

    topics = []
    for i, rec in enumerate(recommendations_raw[:count], start=1):
        topic = ChannelTopic(
            channel_id=channel_id,
            rank=i,
            display_status="shown" if i <= shown_count else "queued",
            title=rec.get("title", "제목 없음"),
            based_on_topic=rec.get("based_on_topic"),
            trend_basis=rec.get("trend_basis"),
            recommendation_reason=rec.get("recommendation_reason"),
            urgency=rec.get("urgency", "normal"),
            search_keywords=rec.get("search_keywords", []),
            content_angles=rec.get("content_angles", []),
            thumbnail_idea=rec.get("thumbnail_idea"),
            created_at=now,
            expires_at=expires_at,
        )
        db.add(topic)
        topics.append(topic)

    await db.commit()

    # shown 상태인 것만 refresh 후 반환
    shown_topics = [t for t in topics if t.display_status == "shown"]
    for t in shown_topics:
        await db.refresh(t)

    return shown_topics


async def generate_trend_topics(
    db: AsyncSession,
    channel_id: str,
    count: int = 10,
    shown_count: int = 2,
) -> List[TrendTopic]:
    """
    트렌드 기반 추천 생성 (일간).

    1. 기존 추천 삭제
    2. Gemini로 추천 생성 (트렌드 중심)
    3. DB에 개별 Row로 저장
    4. shown 상태인 것만 반환
    """
    # 1. 페르소나 조회
    persona = await _get_persona(db, channel_id)
    if not persona:
        return []

    # 2. 기존 추천 삭제
    await _delete_existing_topics(db, channel_id, TrendTopic)

    # 3. Gemini 호출 (트렌드 모드)
    recommendations_raw = await _call_topic_rec(persona, count, trend_focus=True)

    if not recommendations_raw:
        return []

    # 4. DB 저장
    now = datetime.utcnow()
    expires_at = now + timedelta(days=1)  # 일간

    topics = []
    for i, rec in enumerate(recommendations_raw[:count], start=1):
        topic = TrendTopic(
            channel_id=channel_id,
            rank=i,
            display_status="shown" if i <= shown_count else "queued",
            title=rec.get("title", "제목 없음"),
            based_on_topic=rec.get("based_on_topic"),
            trend_basis=rec.get("trend_basis"),
            recommendation_reason=rec.get("recommendation_reason"),
            urgency=rec.get("urgency", "urgent"),  # 트렌드는 기본 urgent
            search_keywords=rec.get("search_keywords", []),
            content_angles=rec.get("content_angles", []),
            thumbnail_idea=rec.get("thumbnail_idea"),
            created_at=now,
            expires_at=expires_at,
        )
        db.add(topic)
        topics.append(topic)

    await db.commit()

    # shown 상태인 것만 refresh 후 반환
    shown_topics = [t for t in topics if t.display_status == "shown"]
    for t in shown_topics:
        await db.refresh(t)

    return shown_topics


# =============================================================================
# 상태 변경 서비스
# =============================================================================

async def skip_topic(
    db: AsyncSession,
    topic_id: str,
    topic_type: str,
) -> Tuple[bool, Optional[ChannelTopic | TrendTopic]]:
    """
    주제 건너뛰기 (개별 새로고침).

    1. 해당 주제: shown → skipped
    2. 다음 queued 주제: queued → shown
    3. 새로 표시된 주제 반환

    Returns:
        (success, new_topic)
    """
    model = ChannelTopic if topic_type == "channel" else TrendTopic

    # 현재 주제 조회
    stmt = select(model).where(model.id == topic_id)
    result = await db.execute(stmt)
    topic = result.scalar_one_or_none()

    if not topic or topic.display_status != "shown":
        return False, None

    # 1. 현재 주제 skipped로 변경
    topic.display_status = "skipped"

    # 2. 다음 queued 주제 찾기
    next_stmt = select(model).where(
        and_(
            model.channel_id == topic.channel_id,
            model.display_status == "queued",
        )
    ).order_by(model.rank).limit(1)

    next_result = await db.execute(next_stmt)
    next_topic = next_result.scalar_one_or_none()

    if next_topic:
        next_topic.display_status = "shown"

    await db.commit()

    if next_topic:
        await db.refresh(next_topic)

    return True, next_topic


async def update_topic_status(
    db: AsyncSession,
    topic_id: str,
    topic_type: str,
    new_status: str,
    scheduled_date: Optional[datetime] = None,
) -> Optional[ChannelTopic | TrendTopic]:
    """
    주제 상태 변경 (확정, 작성중 등).

    Args:
        new_status: "confirmed" / "scripting" / "completed"
        scheduled_date: 확정 시 예정 날짜
    """
    model = ChannelTopic if topic_type == "channel" else TrendTopic

    stmt = select(model).where(model.id == topic_id)
    result = await db.execute(stmt)
    topic = result.scalar_one_or_none()

    if not topic:
        return None

    topic.status = new_status

    if new_status == "confirmed":
        topic.confirmed_at = datetime.utcnow()
        if scheduled_date:
            topic.scheduled_date = scheduled_date

    await db.commit()
    await db.refresh(topic)

    return topic


# =============================================================================
# 헬퍼 함수
# =============================================================================

async def _get_persona(db: AsyncSession, channel_id: str) -> Optional[ChannelPersona]:
    """채널 페르소나 조회."""
    stmt = select(ChannelPersona).where(ChannelPersona.channel_id == channel_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _delete_existing_topics(db: AsyncSession, channel_id: str, model):
    """기존 추천 주제 삭제."""
    stmt = delete(model).where(model.channel_id == channel_id)
    await db.execute(stmt)


async def _call_topic_rec(
    persona: ChannelPersona,
    count: int,
    trend_focus: bool = False,
) -> List[dict]:
    """
    topic_rec 모듈 호출 (Gemini 추천 생성).

    Args:
        persona: 채널 페르소나
        count: 생성할 추천 개수
        trend_focus: True면 트렌드 중심 추천
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    # 페르소나에서 카테고리 추출
    preferred_categories = persona.preferred_categories or persona.analyzed_categories or []
    preferred_subcategories = persona.preferred_subcategories or persona.analyzed_subcategories or []

    def run_topic_rec():
        """topic_rec 실행 (동기)."""
        try:
            from src.topic_rec.graph import topic_rec_graph

            persona_config = {
                "channel_name": persona.one_liner or "Unknown",
                "preferred_categories": preferred_categories,
                "preferred_subcategories": preferred_subcategories,
                "trend_focus": trend_focus,
            }

            initial_state = {
                "persona": persona_config,
                "trends": [],
                "processed_trends": [],
                "category_clusters": [],
                "clusters": [],
                "insights": {},
                "recommendations": [],
                "retry_count": 0,
                "error": None,
                "current_step": "init",
            }

            # 그래프 실행
            final_state = topic_rec_graph.invoke(initial_state)

            return final_state.get("recommendations", [])
        except Exception as e:
            print(f"topic_rec error: {e}")
            return []

    # ThreadPoolExecutor로 동기 함수 실행
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        recommendations_raw = await loop.run_in_executor(executor, run_topic_rec)

    return recommendations_raw[:count]


# =============================================================================
# 레거시 호환 함수 (기존 API 지원)
# =============================================================================

async def get_recommendations_legacy(
    db: AsyncSession,
    channel_id: str,
) -> Optional[dict]:
    """
    레거시 API용 추천 조회.

    기존 형식으로 변환하여 반환합니다.
    """
    channel_topics, trend_topics = await get_shown_topics(db, channel_id)

    if not channel_topics and not trend_topics:
        return None

    # 기존 형식으로 변환
    recommendations = []
    for topic in channel_topics + trend_topics:
        recommendations.append({
            "title": topic.title,
            "based_on_topic": topic.based_on_topic,
            "trend_basis": topic.trend_basis,
            "recommendation_reason": topic.recommendation_reason,
            "urgency": topic.urgency,
            "search_keywords": topic.search_keywords,
            "content_angles": topic.content_angles,
            "thumbnail_idea": topic.thumbnail_idea,
        })

    # 만료 시간 (가장 빠른 것 기준)
    all_topics = channel_topics + trend_topics
    expires_at = min(t.expires_at for t in all_topics) if all_topics else datetime.utcnow()
    generated_at = min(t.created_at for t in all_topics) if all_topics else datetime.utcnow()

    return {
        "channel_id": channel_id,
        "recommendations": recommendations,
        "generated_at": generated_at,
        "expires_at": expires_at,
        "is_expired": expires_at < datetime.utcnow(),
    }


async def generate_recommendations_legacy(
    db: AsyncSession,
    channel_id: str,
) -> Optional[dict]:
    """
    레거시 API용 추천 생성.

    채널 맞춤 + 트렌드 모두 생성 후 기존 형식으로 반환.
    """
    # 채널 맞춤 5개 + 트렌드 2개 생성
    channel_topics = await generate_channel_topics(db, channel_id, count=10, shown_count=5)
    trend_topics = await generate_trend_topics(db, channel_id, count=10, shown_count=2)

    return await get_recommendations_legacy(db, channel_id)
