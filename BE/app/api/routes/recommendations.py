"""
트렌드 기반 주제 추천 API 라우터
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
    RecommendationResponse,
    RecommendationGenerateResponse,
    RecommendationItem,
    SearchKeywords,
)
from app.services.recommendation_service import (
    get_recommendations,
    generate_recommendations,
)


router = APIRouter(prefix="/recommendations", tags=["recommendations"])


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


def _convert_to_response(recommendation) -> RecommendationResponse:
    """DB 모델을 API 응답으로 변환."""
    items = []
    for rec in recommendation.recommendations:
        # search_keywords 변환
        search_keywords = None
        if rec.get("search_keywords"):
            search_keywords = SearchKeywords(
                youtube=rec["search_keywords"].get("youtube", []),
                google=rec["search_keywords"].get("google", []),
            )

        items.append(RecommendationItem(
            title=rec.get("title", ""),
            based_on_topic=rec.get("based_on_topic", ""),
            trend_basis=rec.get("trend_basis", ""),
            recommendation_reason=rec.get("recommendation_reason"),
            search_keywords=search_keywords,
            content_angles=rec.get("content_angles", []),
            thumbnail_idea=rec.get("thumbnail_idea"),
            urgency=rec.get("urgency", "normal"),
        ))

    return RecommendationResponse(
        channel_id=recommendation.channel_id,
        recommendations=items,
        generated_at=recommendation.generated_at,
        expires_at=recommendation.expires_at,
        is_expired=recommendation.is_expired(),
    )


@router.get("", response_model=RecommendationResponse)
async def get_my_recommendations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    내 채널 추천 조회.

    - 추천 결과가 없으면 404 반환
    - 만료되었어도 기존 데이터 반환 (is_expired=true)
    - 새로 생성하려면 POST /recommendations/generate 사용
    """
    channel_id = await _get_user_channel_id(db, current_user)
    recommendation = await get_recommendations(db, channel_id)

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="추천 결과가 없습니다. POST /recommendations/generate를 호출해주세요.",
        )

    return _convert_to_response(recommendation)


@router.post("/generate", response_model=RecommendationGenerateResponse)
async def generate_my_recommendations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    트렌드 기반 주제 추천 생성.

    1. 페르소나에서 선호 카테고리 조회
    2. topic_rec 모듈로 트렌드 분석 + 추천 생성
    3. 결과 저장 (24시간 후 만료)

    기존 추천이 있으면 덮어씁니다.
    """
    channel_id = await _get_user_channel_id(db, current_user)

    try:
        recommendation = await generate_recommendations(
            db=db,
            channel_id=channel_id,
            max_recommendations=2,  # 데모용 2개
        )

        if not recommendation:
            return RecommendationGenerateResponse(
                success=False,
                message="추천 생성에 실패했습니다. 페르소나가 먼저 생성되어 있어야 합니다.",
                data=None,
            )

        return RecommendationGenerateResponse(
            success=True,
            message="추천이 성공적으로 생성되었습니다.",
            data=_convert_to_response(recommendation),
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
    추천 상태 확인 (FE 로딩 판단용).

    응답:
    - exists: 추천 결과 존재 여부
    - is_expired: 만료 여부
    - generated_at: 생성 시간
    - expires_at: 만료 시간
    """
    channel_id = await _get_user_channel_id(db, current_user)
    recommendation = await get_recommendations(db, channel_id)

    if not recommendation:
        return {
            "exists": False,
            "is_expired": None,
            "generated_at": None,
            "expires_at": None,
        }

    return {
        "exists": True,
        "is_expired": recommendation.is_expired(),
        "generated_at": recommendation.generated_at,
        "expires_at": recommendation.expires_at,
    }
