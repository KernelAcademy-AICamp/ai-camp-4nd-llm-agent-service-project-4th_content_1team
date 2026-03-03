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
    ManualPersonaRequest,
)
from app.services.persona_service import (
    generate_persona,
    get_persona,
    update_persona,
)
from app.services.channel_video_service import sync_channel_videos
from app.services.shared_state_service import SharedStateService
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
        analyzed_categories=persona.analyzed_categories,
        analyzed_subcategories=persona.analyzed_subcategories,
        preferred_categories=persona.preferred_categories,
        preferred_subcategories=persona.preferred_subcategories,
        topic_keywords=persona.topic_keywords,
        style_keywords=persona.style_keywords,
        video_types=persona.video_types,
        content_structures=persona.content_structures,
        tone_manner=persona.tone_manner,
        tone_samples=persona.tone_samples,
        hit_patterns=persona.hit_patterns,
        low_patterns=persona.low_patterns,
        success_formula=persona.success_formula,
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

        # 페르소나 재생성 시 Redis 캐시 무효화
        await SharedStateService.invalidate_channel_profile(str(current_user.id))

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
                analyzed_categories=persona.analyzed_categories,
                analyzed_subcategories=persona.analyzed_subcategories,
                preferred_categories=persona.preferred_categories,
                preferred_subcategories=persona.preferred_subcategories,
                topic_keywords=persona.topic_keywords,
                style_keywords=persona.style_keywords,
                video_types=persona.video_types,
                content_structures=persona.content_structures,
                tone_manner=persona.tone_manner,
                tone_samples=persona.tone_samples,
                hit_patterns=persona.hit_patterns,
                low_patterns=persona.low_patterns,
                success_formula=persona.success_formula,
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


@router.post("/generate-from-manual", response_model=PersonaGenerateResponse)
async def generate_manual_persona(
    request: ManualPersonaRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    수동 온보딩 페르소나 생성 (Branch B).

    LLM 호출 없이 유저 입력값을 템플릿으로 매핑하여 페르소나를 생성합니다.
    채널이 없는 유저는 placeholder 채널을 자동 생성합니다.
    """
    from app.services.persona_service import _save_persona

    try:
        # 1. 유저의 채널 조회 → 없으면 placeholder 생성
        stmt = select(YouTubeChannel).where(YouTubeChannel.user_id == current_user.id)
        result = await db.execute(stmt)
        channel = result.scalar_one_or_none()

        if not channel:
            placeholder_id = f"manual_{current_user.id}"
            channel = YouTubeChannel(
                channel_id=placeholder_id,
                user_id=current_user.id,
                title="수동 입력 채널",
                description="온보딩 수동 입력으로 생성된 플레이스홀더",
                raw_channel_json={"type": "manual_placeholder"},
            )
            db.add(channel)
            await db.commit()

        # 2. 타겟 시청자 문자열 생성
        gender_map = {"male": "남성", "female": "여성", "any": "전체"}
        gender_kr = gender_map.get(request.gender, request.gender)
        target_audience = f"{request.age_group}세 {gender_kr}"

        # 3. 템플릿으로 persona_summary 생성
        categories_str = ", ".join(request.categories)
        topics_str = ", ".join(request.topic_keywords)
        styles_str = ", ".join(request.style_keywords)
        persona_summary = (
            f"{categories_str} 분야에서 {topics_str}을(를) 주제로 "
            f"{styles_str} 스타일의 콘텐츠를 제작하는 채널입니다. "
            f"주요 타겟은 {target_audience} 시청자입니다."
        )

        # 4. 입력값 → 페르소나 필드 매핑
        persona_data = {
            "persona_summary": persona_summary,
            "one_liner": f"{categories_str} 크리에이터",
            "main_topics": request.topic_keywords,
            "content_style": styles_str,
            "target_audience": target_audience,
            "analyzed_categories": request.categories,
            "topic_keywords": request.topic_keywords,
            "style_keywords": request.style_keywords,
            "preferred_categories": request.categories,
        }

        # 5. DB 저장 (기존 _save_persona 재사용)
        persona = await _save_persona(db, channel.channel_id, persona_data)

        # 6. Redis 캐시 무효화
        await SharedStateService.invalidate_channel_profile(str(current_user.id))

        return PersonaGenerateResponse(
            success=True,
            message="수동 온보딩 페르소나가 생성되었습니다.",
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
                analyzed_categories=persona.analyzed_categories,
                analyzed_subcategories=persona.analyzed_subcategories,
                preferred_categories=persona.preferred_categories,
                preferred_subcategories=persona.preferred_subcategories,
                topic_keywords=persona.topic_keywords,
                style_keywords=persona.style_keywords,
                video_types=persona.video_types,
                content_structures=persona.content_structures,
                tone_manner=persona.tone_manner,
                tone_samples=persona.tone_samples,
                hit_patterns=persona.hit_patterns,
                low_patterns=persona.low_patterns,
                success_formula=persona.success_formula,
                created_at=persona.created_at,
                updated_at=persona.updated_at,
            ),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"수동 페르소나 생성 중 오류가 발생했습니다: {str(e)}",
        )


@router.get("/channel-profile")
async def get_channel_profile_for_agents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    에이전트 입력용 채널 프로필 조회.

    Redis shared_state에서 우선 조회하고, 없으면 DB에서 빌드 후 캐시합니다.
    페르소나 재생성/수정 시 캐시가 자동 무효화되므로 항상 최신 데이터를 반환합니다.
    """
    from src.script_gen.utils.input_builder import _get_user_channel, _build_channel_profile

    user_id = str(current_user.id)

    # 1. Redis 캐시 우선 조회
    cached = await SharedStateService.get_channel_profile(user_id)
    if cached:
        return cached

    # 2. 캐시 미스 → DB 조회
    channel = await _get_user_channel(db, user_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="연결된 YouTube 채널이 없습니다.",
        )

    persona = await get_persona(db, channel.channel_id)
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="페르소나가 생성되지 않았습니다. POST /personas/generate를 먼저 호출해주세요.",
        )

    profile = _build_channel_profile(channel, persona)
    profile["channel_id"] = channel.channel_id

    # 3. Redis 저장
    await SharedStateService.set_channel_profile(user_id, profile)
    return profile


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

    # 페르소나 수정 시 Redis 캐시 무효화
    await SharedStateService.invalidate_channel_profile(str(current_user.id))

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
        analyzed_categories=persona.analyzed_categories,
        analyzed_subcategories=persona.analyzed_subcategories,
        preferred_categories=persona.preferred_categories,
        preferred_subcategories=persona.preferred_subcategories,
        topic_keywords=persona.topic_keywords,
        style_keywords=persona.style_keywords,
        video_types=persona.video_types,
        content_structures=persona.content_structures,
        tone_manner=persona.tone_manner,
        tone_samples=persona.tone_samples,
        hit_patterns=persona.hit_patterns,
        low_patterns=persona.low_patterns,
        success_formula=persona.success_formula,
        created_at=persona.created_at,
        updated_at=persona.updated_at,
    )
