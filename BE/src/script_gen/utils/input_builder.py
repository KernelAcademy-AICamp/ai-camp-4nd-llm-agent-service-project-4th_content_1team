"""
Planner Input Builder

DB에서 데이터를 조회하여 Planner 에이전트 입력 형식으로 변환합니다.
"""

from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.models.youtube_channel import YouTubeChannel
from app.models.channel_persona import ChannelPersona
from app.models.content_topic import ChannelTopic, TrendTopic

logger = logging.getLogger(__name__)


class PlannerInputBuildError(Exception):
    """Planner 입력 생성 중 발생하는 에러"""
    pass


async def build_planner_input(
    db: AsyncSession,
    topic: str,
    user_id: str,
    topic_recommendation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Planner 에이전트 입력 데이터를 생성합니다.

    1. Redis shared_state에서 channel_profile 조회 (캐시 HIT → DB 생략)
    2. 캐시 MISS → DB에서 채널 + 페르소나 조회 후 Redis에 저장
    3. topic_context는 topic_recommendation_id가 있을 때만 DB 조회

    Args:
        db: 데이터베이스 세션
        topic: 영상 주제
        user_id: 사용자 ID
        topic_recommendation_id: AI 추천 주제 ID (선택)

    Returns:
        planner_input dict

    Raises:
        PlannerInputBuildError: 필수 데이터가 없거나 조회 실패 시
    """
    from app.services.shared_state_service import SharedStateService

    try:
        # ── 1. Redis shared_state 조회 ────────────────────────────────────────
        channel_profile = await SharedStateService.get_channel_profile(user_id)
        channel_id: Optional[str] = None

        if channel_profile:
            # 캐시 HIT: DB 채널/페르소나 조회 생략
            channel_id = channel_profile.get("channel_id")
            logger.info(
                f"[SharedState] HIT — channel/persona DB 조회 생략 "
                f"(user={user_id}, channel_id={channel_id})"
            )

            # channel_id가 캐시에 없는 예외 상황 처리
            if not channel_id and topic_recommendation_id:
                channel = await _get_user_channel(db, user_id)
                channel_id = channel.channel_id if channel else None

        else:
            # ── 2. 캐시 MISS: DB 조회 후 Redis 저장 ──────────────────────────
            channel = await _get_user_channel(db, user_id)
            if not channel:
                raise PlannerInputBuildError(
                    f"사용자 {user_id}의 연결된 YouTube 채널을 찾을 수 없습니다. "
                    "먼저 채널을 연결해주세요."
                )
            logger.info(f"[SharedState] MISS — DB 조회: {channel.title} ({channel.channel_id})")

            persona = await _get_channel_persona(db, channel.channel_id)
            if not persona:
                raise PlannerInputBuildError(
                    f"채널 '{channel.title}'의 페르소나를 찾을 수 없습니다. "
                    "먼저 채널 분석을 완료해주세요."
                )

            channel_profile = _build_channel_profile(channel, persona)
            channel_profile["channel_id"] = channel.channel_id
            channel_id = channel.channel_id

            # Redis에 저장 (실패해도 무시)
            await SharedStateService.set_channel_profile(user_id, channel_profile)

        # ── 3. topic_context 구성 (AI 추천 시만) ──────────────────────────────
        topic_context = None
        if topic_recommendation_id and channel_id:
            topic_context = await _build_topic_context(
                db,
                channel_id,
                topic_recommendation_id,
            )

        planner_input = {
            "topic": topic,
            "channel_profile": channel_profile,
            "topic_context": topic_context,
        }

        logger.info(
            f"Planner input 구성 완료 — topic={topic!r}, "
            f"has_context={topic_context is not None}"
        )
        return planner_input

    except PlannerInputBuildError:
        raise

    except Exception as e:
        logger.error(f"Unexpected error building planner input: {e}", exc_info=True)
        raise PlannerInputBuildError(
            "콘텐츠 기획 준비 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        )


# =============================================================================
# 헬퍼 함수들
# =============================================================================

async def _get_user_channel(
    db: AsyncSession, 
    user_id: str
) -> Optional[YouTubeChannel]:
    """사용자의 YouTube 채널 조회"""
    result = await db.execute(
        select(YouTubeChannel).where(YouTubeChannel.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def _get_channel_persona(
    db: AsyncSession, 
    channel_id: str
) -> Optional[ChannelPersona]:
    """채널 페르소나 조회"""
    result = await db.execute(
        select(ChannelPersona).where(ChannelPersona.channel_id == channel_id)
    )
    return result.scalar_one_or_none()


def _build_channel_profile(
    channel: YouTubeChannel, 
    persona: ChannelPersona
) -> Dict[str, Any]:
    """
    채널 프로필 구성
    
    필수/권장/선택 필드를 모두 포함하되, None 값은 제외합니다.
    """
    
    # 카테고리 결정 (우선순위: preferred > analyzed > "general")
    category = "general"
    if persona.preferred_categories and len(persona.preferred_categories) > 0:
        category = persona.preferred_categories[0]
    elif persona.analyzed_categories and len(persona.analyzed_categories) > 0:
        category = persona.analyzed_categories[0]
    
    # 기본 프로필 (필수 필드)
    profile = {
        "name": channel.title or "Unknown Channel",
        "category": category,
        "target_audience": persona.target_audience or "일반 시청자",
    }
    
    # 권장 필드 추가 (값이 있을 때만)
    if persona.content_style:
        profile["content_style"] = persona.content_style
    
    if persona.main_topics:
        profile["main_topics"] = persona.main_topics
    
    if persona.optimal_duration:
        profile["average_duration"] = persona.optimal_duration
    
    # 선택 필드 추가 (값이 있을 때만)
    if persona.one_liner:
        profile["one_liner"] = persona.one_liner
    
    if persona.persona_summary:
        profile["persona_summary"] = persona.persona_summary
    
    if persona.hit_topics:
        profile["hit_topics"] = persona.hit_topics
    
    if persona.audience_needs:
        profile["audience_needs"] = persona.audience_needs
    
    if persona.differentiator:
        profile["differentiator"] = persona.differentiator
    
    if persona.title_patterns:
        profile["title_patterns"] = persona.title_patterns
    
    # 톤/말투 필드 (자막 분석 기반 — video_analyzer에서 생성)
    if persona.tone_manner:
        profile["tone_manner"] = persona.tone_manner
    
    if persona.tone_samples:
        profile["tone_samples"] = persona.tone_samples
    
    # 영상 분석 결과 필드 (히트/저조 패턴, 영상 유형 등)
    if persona.video_types:
        profile["video_types"] = persona.video_types
    
    if persona.content_structures:
        profile["content_structures"] = persona.content_structures
    
    if persona.hit_patterns:
        profile["hit_patterns"] = persona.hit_patterns
    
    if persona.low_patterns:
        profile["low_patterns"] = persona.low_patterns
    
    if persona.success_formula:
        profile["success_formula"] = persona.success_formula
    
    return profile


async def _build_topic_context(
    db: AsyncSession,
    channel_id: str,
    topic_recommendation_id: str,
) -> Optional[Dict[str, Any]]:
    """
    주제 컨텍스트 구성 (AI 추천 주제 선택 시)
    
    Args:
        db: 데이터베이스 세션
        channel_id: 채널 ID
        topic_recommendation_id: 추천 주제 ID (recommendations 배열의 인덱스 또는 특정 식별자)
    
    Returns:
        topic_context dict 또는 None (조회 실패 시)
    """
    
    try:
        # ChannelTopic에서 먼저 조회 시도
        result = await db.execute(
            select(ChannelTopic).where(
                ChannelTopic.id == topic_recommendation_id
            )
        )
        topic = result.scalar_one_or_none()
        
        # ChannelTopic에 없으면 TrendTopic에서 조회
        if not topic:
            result = await db.execute(
                select(TrendTopic).where(
                    TrendTopic.id == topic_recommendation_id
                )
            )
            topic = result.scalar_one_or_none()
        
        if not topic:
            logger.warning(f"No topic found with id {topic_recommendation_id}")
            return None
        
        # topic_context 구성
        context = {
            "source": "ai_recommendation",
            "trend_basis": topic.trend_basis or "",
            "urgency": topic.urgency or "normal",
            "content_angles": topic.content_angles or [],
            "recommendation_reason": topic.recommendation_reason or "",
            "search_keywords": topic.search_keywords or [],  # channel_topics/trend_topics 테이블의 뉴스 검색 키워드
            "based_on_topic": topic.based_on_topic or "",  # 어떤 트렌드 기반인지
        }
        
        return context
    
    except Exception as e:
        logger.error(f"Error building topic context: {e}", exc_info=True)
        # topic_context는 선택 사항이므로 에러 시 None 반환
        return None


# =============================================================================
# 편의 함수 (직접 입력 시나리오)
# =============================================================================

async def build_planner_input_from_user_input(
    db: AsyncSession,
    topic: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    사용자 직접 입력 시나리오용 편의 함수
    
    topic_context 없이 planner_input을 생성합니다.
    """
    return await build_planner_input(
        db=db,
        topic=topic,
        user_id=user_id,
        topic_recommendation_id=None,  # 직접 입력이므로 None
    )
