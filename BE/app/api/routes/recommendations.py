"""
콘텐츠 주제 추천 API 라우터

채널 맞춤 추천(주간)과 트렌드 기반 추천(일간)을 관리합니다.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.youtube_channel import YouTubeChannel
from app.schemas.recommendation import (
    TopicsListResponse,
    ChannelTopicResponse,
    TrendTopicResponse,
    TopicStatusUpdate,
    TopicSkipResponse,
    TrendTopicsGenerateResponse,
    # 레거시 호환
    RecommendationResponse,
    RecommendationGenerateResponse,
    RecommendationItem,
)
from app.services.recommendation_service import (
    get_shown_topics,
    check_recommendations_exist,
    generate_trend_topics,
    skip_topic,
    update_topic_status,
    # 레거시 호환
    get_recommendations_legacy,
    generate_recommendations_legacy,
)


router = APIRouter(prefix="/recommendations", tags=["recommendations"])


# =============================================================================
# 헬퍼 함수
# =============================================================================

async def _get_user_channel_id(
    db: AsyncSession,
    user: User,
) -> str:
    """사용자의 YouTube 채널 ID 조회."""
    stmt = select(YouTubeChannel).where(YouTubeChannel.user_id == user.id)
    result = await db.execute(stmt)
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="연결된 YouTube 채널이 없습니다.",
        )

    return channel.channel_id


def _topic_to_response(topic, topic_type: str) -> dict:
    """DB 모델을 응답 딕셔너리로 변환."""
    return {
        "id": str(topic.id),
        "channel_id": topic.channel_id,
        "rank": topic.rank,
        "display_status": topic.display_status,
        "title": topic.title,
        "based_on_topic": topic.based_on_topic,
        "trend_basis": topic.trend_basis,
        "recommendation_reason": topic.recommendation_reason,
        "recommendation_type": getattr(topic, "recommendation_type", None),
        "recommendation_direction": getattr(topic, "recommendation_direction", None),
        "source_layer": getattr(topic, "source_layer", None),
        "urgency": topic.urgency,
        "search_keywords": topic.search_keywords or [],
        "content_angles": topic.content_angles or [],
        "thumbnail_idea": topic.thumbnail_idea,
        "status": topic.status,
        "scheduled_date": topic.scheduled_date,
        "created_at": topic.created_at,
        "expires_at": topic.expires_at,
        "confirmed_at": topic.confirmed_at,
        "topic_type": topic_type,
    }


# =============================================================================
# 신규 API (개별 주제 관리)
# =============================================================================

@router.get("/topics", response_model=TopicsListResponse)
async def get_all_topics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    전체 추천 주제 조회 (채널 맞춤 + 트렌드).

    - shown 상태인 주제만 반환
    - 채널 맞춤: 최대 5개
    - 트렌드: 최대 2개
    """
    channel_id = await _get_user_channel_id(db, current_user)
    channel_topics, trend_topics = await get_shown_topics(db, channel_id)

    return TopicsListResponse(
        channel_topics=[
            ChannelTopicResponse(**_topic_to_response(t, "channel"))
            for t in channel_topics
        ],
        trend_topics=[
            TrendTopicResponse(**_topic_to_response(t, "trend"))
            for t in trend_topics
        ],
        channel_expires_at=channel_topics[0].expires_at if channel_topics else None,
        trend_expires_at=trend_topics[0].expires_at if trend_topics else None,
    )


@router.post("/topics/trend/generate", response_model=TrendTopicsGenerateResponse)
async def generate_trend_recommendations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    트렌드 기반 추천 생성 (일간).

    - 10개 생성, 2개 표시
    - 기존 트렌드 추천은 삭제됨
    """
    channel_id = await _get_user_channel_id(db, current_user)

    try:
        topics = await generate_trend_topics(
            db=db,
            channel_id=channel_id,
            count=10,
            shown_count=2,
        )

        if not topics:
            return TrendTopicsGenerateResponse(
                success=False,
                message="추천 생성에 실패했습니다. 페르소나가 먼저 생성되어 있어야 합니다.",
                generated_count=0,
                shown_count=0,
                topics=[],
            )

        return TrendTopicsGenerateResponse(
            success=True,
            message="트렌드 추천이 성공적으로 생성되었습니다.",
            generated_count=10,
            shown_count=len(topics),
            topics=[
                TrendTopicResponse(**_topic_to_response(t, "trend"))
                for t in topics
            ],
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"추천 생성 중 오류가 발생했습니다: {str(e)}",
        )


@router.post("/topics/{topic_type}/{topic_id}/skip", response_model=TopicSkipResponse)
async def skip_recommendation(
    topic_type: str,
    topic_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    주제 건너뛰기 (개별 새로고침).

    - 해당 주제: shown → skipped
    - 다음 대기 주제: queued → shown
    - topic_type: "channel" 또는 "trend"
    """
    if topic_type not in ["channel", "trend"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="topic_type은 'channel' 또는 'trend'여야 합니다.",
        )

    success, new_topic = await skip_topic(db, topic_id, topic_type)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="주제를 찾을 수 없거나 이미 건너뛴 주제입니다.",
        )

    # 남은 queued 개수 계산 (간단히 new_topic 존재 여부로 판단)
    remaining = 1 if new_topic else 0

    return TopicSkipResponse(
        skipped_topic_id=topic_id,
        new_topic=_topic_to_response(new_topic, topic_type) if new_topic else None,
        remaining_queued=remaining,
    )


@router.patch("/topics/{topic_type}/{topic_id}/status")
async def update_topic_status_endpoint(
    topic_type: str,
    topic_id: str,
    update: TopicStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    주제 상태 변경.

    - status: "confirmed" / "scripting" / "completed"
    - scheduled_date: 확정 시 예정 날짜 (선택)
    """
    if topic_type not in ["channel", "trend"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="topic_type은 'channel' 또는 'trend'여야 합니다.",
        )

    topic = await update_topic_status(
        db=db,
        topic_id=topic_id,
        topic_type=topic_type,
        new_status=update.status,
        scheduled_date=update.scheduled_date,
    )

    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="주제를 찾을 수 없습니다.",
        )

    return _topic_to_response(topic, topic_type)


@router.get("/topics/status")
async def get_topics_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    추천 상태 확인 (FE 로딩 판단용).

    응답:
    - channel_exists: 채널 맞춤 추천 존재 여부
    - channel_expired: 채널 맞춤 추천 만료 여부
    - trend_exists: 트렌드 추천 존재 여부
    - trend_expired: 트렌드 추천 만료 여부
    """
    channel_id = await _get_user_channel_id(db, current_user)
    status_info = await check_recommendations_exist(db, channel_id)

    return status_info


# =============================================================================
# 레거시 API (기존 FE 호환)
# =============================================================================

@router.get("", response_model=RecommendationResponse)
async def get_my_recommendations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    [레거시] 내 채널 추천 조회.

    기존 형식으로 반환합니다. 신규 개발에서는 GET /topics 사용을 권장합니다.
    """
    channel_id = await _get_user_channel_id(db, current_user)
    result = await get_recommendations_legacy(db, channel_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="추천 결과가 없습니다. POST /recommendations/generate를 호출해주세요.",
        )

    return RecommendationResponse(
        channel_id=result["channel_id"],
        recommendations=[
            RecommendationItem(**rec) for rec in result["recommendations"]
        ],
        generated_at=result["generated_at"],
        expires_at=result["expires_at"],
        is_expired=result["is_expired"],
    )


@router.post("/generate", response_model=RecommendationGenerateResponse)
async def generate_my_recommendations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    [레거시] 트렌드 기반 주제 추천 생성.

    기존 형식으로 반환합니다. 신규 개발에서는 POST /topics/trend/generate 사용을 권장합니다.
    """
    channel_id = await _get_user_channel_id(db, current_user)

    try:
        result = await generate_recommendations_legacy(db, channel_id)

        if not result:
            return RecommendationGenerateResponse(
                success=False,
                message="추천 생성에 실패했습니다. 페르소나가 먼저 생성되어 있어야 합니다.",
                data=None,
            )

        return RecommendationGenerateResponse(
            success=True,
            message="추천이 성공적으로 생성되었습니다.",
            data=RecommendationResponse(
                channel_id=result["channel_id"],
                recommendations=[
                    RecommendationItem(**rec) for rec in result["recommendations"]
                ],
                generated_at=result["generated_at"],
                expires_at=result["expires_at"],
                is_expired=result["is_expired"],
            ),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"추천 생성 중 오류가 발생했습니다: {str(e)}",
        )


@router.get("/status")
async def get_recommendation_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    [레거시] 추천 상태 확인.

    신규 개발에서는 GET /topics/status 사용을 권장합니다.
    """
    channel_id = await _get_user_channel_id(db, current_user)
    status_info = await check_recommendations_exist(db, channel_id)

    # 레거시 형식으로 변환
    exists = status_info["trend_exists"]
    is_expired = status_info["trend_expired"]

    return {
        "exists": exists,
        "is_expired": is_expired if exists else None,
        "generated_at": None,  # 새 구조에서는 개별 조회 필요
        "expires_at": None,
    }
