"""
썸네일 생성 API 라우트.

SSE(Server-Sent Events) 기반으로 실시간 진행 상황을 프론트엔드에 전달.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.thumbnail_service import generate_thumbnail_stream

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/thumbnail", tags=["thumbnail"])


class ThumbnailRequest(BaseModel):
    """썸네일 생성 요청 스키마."""

    topic: str                              # 주제 (예: "2026년 게임 트렌드")
    style: str = "impact"                   # 스타일 (impact, minimal, hot, premium)
    keywords: Optional[list[str]] = None    # 키워드 목록
    tone: Optional[str] = None              # 톤 (예: "긴급", "분석적")
    custom_request: Optional[str] = None    # 사용자 추가 요청


@router.post("/generate-stream")
async def generate_thumbnail_sse(request: ThumbnailRequest):
    """
    SSE 스트리밍으로 썸네일 배경 이미지 생성.

    프론트엔드에서 EventSource로 연결하여 실시간 진행 상황 수신.
    """
    logger.info(f"[Thumbnail] 생성 요청: topic={request.topic}, style={request.style}")

    return StreamingResponse(
        generate_thumbnail_stream(
            topic=request.topic,
            style=request.style,
            keywords=request.keywords,
            tone=request.tone,
            custom_request=request.custom_request,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
