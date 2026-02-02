"""
주제 추천 서비스

topic_rec 모듈을 호출하여 트렌드 기반 추천을 생성하고 저장합니다.
"""
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.topic_recommendation import TopicRecommendation
from app.models.channel_persona import ChannelPersona


async def get_recommendations(
    db: AsyncSession,
    channel_id: str,
) -> Optional[TopicRecommendation]:
    """
    채널의 추천 결과 조회.

    만료되지 않은 추천 결과가 있으면 반환, 없으면 None.
    """
    stmt = select(TopicRecommendation).where(
        TopicRecommendation.channel_id == channel_id
    )
    result = await db.execute(stmt)
    recommendation = result.scalar_one_or_none()

    return recommendation


async def generate_recommendations(
    db: AsyncSession,
    channel_id: str,
    max_recommendations: int = 2,
) -> Optional[TopicRecommendation]:
    """
    트렌드 기반 추천 생성.

    1. 채널 페르소나에서 선호 카테고리 조회
    2. topic_rec 모듈 실행
    3. 결과 저장 및 반환
    """
    # 1. 페르소나 조회
    stmt = select(ChannelPersona).where(ChannelPersona.channel_id == channel_id)
    result = await db.execute(stmt)
    persona = result.scalar_one_or_none()

    if not persona:
        print(f"Persona not found for channel: {channel_id}")
        return None

    # 페르소나에서 카테고리 추출
    preferred_categories = persona.analyzed_categories or []
    preferred_subcategories = persona.analyzed_subcategories or []

    # 사용자 선호 카테고리가 있으면 우선 사용
    if persona.preferred_categories:
        preferred_categories = persona.preferred_categories
    if persona.preferred_subcategories:
        preferred_subcategories = persona.preferred_subcategories

    # 2. topic_rec 모듈 실행 (동기 함수이므로 run_in_executor 사용)
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    def run_topic_rec():
        """topic_rec 실행 (동기)."""
        try:
            from src.topic_rec.graph import topic_rec_graph

            # 페르소나 설정
            persona_config = {
                "channel_name": persona.one_liner or "Unknown",
                "preferred_categories": preferred_categories,
                "preferred_subcategories": preferred_subcategories,
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

    # 추천 개수 제한
    recommendations_raw = recommendations_raw[:max_recommendations]

    # 3. DB 저장 (upsert)
    stmt = select(TopicRecommendation).where(
        TopicRecommendation.channel_id == channel_id
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    now = datetime.utcnow()
    expires_at = now + timedelta(hours=24)

    persona_snapshot = {
        "preferred_categories": preferred_categories,
        "preferred_subcategories": preferred_subcategories,
    }

    if existing:
        # 업데이트
        existing.recommendations = recommendations_raw
        existing.generated_at = now
        existing.expires_at = expires_at
        existing.persona_snapshot = persona_snapshot
        recommendation = existing
    else:
        # 새로 생성
        recommendation = TopicRecommendation(
            channel_id=channel_id,
            recommendations=recommendations_raw,
            generated_at=now,
            expires_at=expires_at,
            persona_snapshot=persona_snapshot,
        )
        db.add(recommendation)

    await db.commit()
    await db.refresh(recommendation)

    return recommendation
