"""
채널 페르소나 API 라우터
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.youtube_channel import YouTubeChannel
from app.schemas.persona import (
    PersonaResponse,
    PersonaUpdateRequest,
    PersonaGenerateResponse,
)
from app.services.persona_service import (
    generate_persona,
    get_persona,
    update_persona,
)
from app.services.channel_video_service import sync_channel_videos
from sqlalchemy import select


router = APIRouter(prefix="/personas", tags=["personas"])


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


@router.get("/me", response_model=PersonaResponse)
async def get_my_persona(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    내 채널 페르소나 조회.

    - 페르소나가 없으면 404 반환
    - 생성은 POST /personas/generate 사용
    """
    channel_id = await _get_user_channel_id(db, current_user)
    persona = await get_persona(db, channel_id)

    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="페르소나가 아직 생성되지 않았습니다. POST /personas/generate를 호출해주세요.",
        )

    return PersonaResponse(
        id=str(persona.id),
        channel_id=persona.channel_id,
        persona_summary=persona.persona_summary,
        one_liner=persona.one_liner,
        main_topics=persona.main_topics,
        content_style=persona.content_style,
        differentiator=persona.differentiator,
        target_audience=persona.target_audience,
        audience_needs=persona.audience_needs,
        hit_topics=persona.hit_topics,
        title_patterns=persona.title_patterns,
        optimal_duration=persona.optimal_duration,
        growth_opportunities=persona.growth_opportunities,
        evidence=persona.evidence,
        topic_keywords=persona.topic_keywords,
        style_keywords=persona.style_keywords,
        created_at=persona.created_at,
        updated_at=persona.updated_at,
    )


@router.post("/generate", response_model=PersonaGenerateResponse)
async def generate_my_persona(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    내 채널 페르소나 생성/재생성.

    1. 채널 영상 동기화 (YouTube API)
    2. 규칙 기반 분석 (4개)
    3. LLM 분석 (3개)
    4. 종합 페르소나 생성

    기존 페르소나가 있으면 덮어씁니다.
    """
    channel_id = await _get_user_channel_id(db, current_user)

    try:
        # 1. 영상 데이터 동기화
        await sync_channel_videos(db, channel_id)

        # 2. 페르소나 생성
        persona = await generate_persona(db, channel_id)

        if not persona:
            return PersonaGenerateResponse(
                success=False,
                message="페르소나 생성에 실패했습니다. 채널 데이터를 확인해주세요.",
                persona=None,
            )

        return PersonaGenerateResponse(
            success=True,
            message="페르소나가 성공적으로 생성되었습니다.",
            persona=PersonaResponse(
                id=str(persona.id),
                channel_id=persona.channel_id,
                persona_summary=persona.persona_summary,
                one_liner=persona.one_liner,
                main_topics=persona.main_topics,
                content_style=persona.content_style,
                differentiator=persona.differentiator,
                target_audience=persona.target_audience,
                audience_needs=persona.audience_needs,
                hit_topics=persona.hit_topics,
                title_patterns=persona.title_patterns,
                optimal_duration=persona.optimal_duration,
                growth_opportunities=persona.growth_opportunities,
                evidence=persona.evidence,
                topic_keywords=persona.topic_keywords,
                style_keywords=persona.style_keywords,
                created_at=persona.created_at,
                updated_at=persona.updated_at,
            ),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"페르소나 생성 중 오류가 발생했습니다: {str(e)}",
        )


@router.patch("/me", response_model=PersonaResponse)
async def update_my_persona(
    request: PersonaUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    내 채널 페르소나 수동 수정.

    분석 결과를 사용자가 직접 수정할 수 있습니다.
    """
    channel_id = await _get_user_channel_id(db, current_user)

    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="수정할 필드가 없습니다.",
        )

    persona = await update_persona(db, channel_id, update_data)

    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="페르소나가 없습니다. 먼저 생성해주세요.",
        )

    return PersonaResponse(
        id=str(persona.id),
        channel_id=persona.channel_id,
        persona_summary=persona.persona_summary,
        one_liner=persona.one_liner,
        main_topics=persona.main_topics,
        content_style=persona.content_style,
        differentiator=persona.differentiator,
        target_audience=persona.target_audience,
        audience_needs=persona.audience_needs,
        hit_topics=persona.hit_topics,
        title_patterns=persona.title_patterns,
        optimal_duration=persona.optimal_duration,
        growth_opportunities=persona.growth_opportunities,
        evidence=persona.evidence,
        topic_keywords=persona.topic_keywords,
        style_keywords=persona.style_keywords,
        created_at=persona.created_at,
        updated_at=persona.updated_at,
    )
