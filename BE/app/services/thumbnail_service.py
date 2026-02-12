"""
썸네일 생성 서비스 (Thumbnail Generation Service).

- Prompt Specialist: Claude로 나노바나나 프로용 영어 프롬프트 생성
- Image Generator: 나노바나나 프로(Gemini 3 Pro Image)로 배경 이미지 생성
- SSE 스트리밍으로 진행 상황 전달
"""
import asyncio
import base64
import json
import logging
import uuid
from pathlib import Path
from typing import AsyncGenerator, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# 이미지 저장 디렉토리
THUMBNAIL_DIR = Path(__file__).parent.parent.parent / "public" / "thumbnails"
THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)


async def build_image_prompt(
    topic: str,
    style: str,
    keywords: list[str] | None = None,
    tone: str | None = None,
    custom_request: str | None = None,
) -> str:
    """
    나노바나나 프로용 이미지 프롬프트를 템플릿 기반으로 생성.

    별도 LLM 호출 없이 바로 프롬프트를 구성.
    텍스트는 프론트에서 오버레이하므로, 이미지에 텍스트 포함하지 않도록 지시.
    """
    style_mapping = {
        "impact": "Bold, dramatic, high contrast, cinematic lighting with vibrant neon colors, dynamic composition, epic and powerful atmosphere",
        "minimal": "Clean, minimalist, soft pastel gradients, modern aesthetic, plenty of negative space, elegant and refined",
        "hot": "Trendy, energetic, warm red and orange tones, dynamic diagonal angles, exciting and urgent feel, breaking news style",
        "premium": "Luxurious, golden and dark tones, sophisticated, professional editorial quality, polished and high-end",
    }

    style_desc = style_mapping.get(style, style_mapping["impact"])
    keyword_str = ", ".join(keywords) if keywords else topic
    tone_str = tone or "professional"
    custom_str = f", {custom_request}" if custom_request else ""

    prompt = (
        f"Create a YouTube thumbnail background image. "
        f"Topic: {topic}. "
        f"Visual style: {style_desc}. "
        f"Visual elements related to: {keyword_str}. "
        f"Mood: {tone_str}{custom_str}. "
        f"IMPORTANT: Do NOT include any text, letters, numbers, or words in the image. "
        f"Leave the center area slightly darker with visual space for text overlay. "
        f"16:9 aspect ratio, cinematic quality, professional photography, 4K quality, "
        f"eye-catching and click-worthy YouTube thumbnail background."
    )

    logger.info(f"[Thumbnail] 프롬프트 생성 완료: {prompt[:100]}...")
    return prompt


async def generate_thumbnail_image(prompt: str) -> Optional[str]:
    """
    나노바나나 프로(Gemini 3 Pro Image)로 배경 이미지 생성.

    Returns:
        저장된 이미지의 상대 경로 (예: /thumbnails/abc123.png) 또는 None
    """
    api_key = settings.nano_banana_api_key
    if not api_key:
        logger.error("[Thumbnail] NANO_BANANA_API_KEY가 설정되지 않았습니다")
        return None

    try:
        # Google GenAI REST API 직접 호출
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}"

        body = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseModalities": ["IMAGE", "TEXT"],
                "imageSizeOptions": {
                    "aspectRatio": "LANDSCAPE_16_9"
                }
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=body)

        if response.status_code != 200:
            logger.error(
                f"[Thumbnail] NanoBanana API 에러: {response.status_code} "
                f"{response.text[:300]}"
            )
            return None

        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            logger.error("[Thumbnail] 응답에 candidates 없음")
            return None

        # 이미지 데이터 추출
        parts = candidates[0].get("content", {}).get("parts", [])
        image_data = None
        for part in parts:
            if "inlineData" in part:
                image_data = part["inlineData"]["data"]
                mime_type = part["inlineData"].get("mimeType", "image/png")
                break

        if not image_data:
            logger.error("[Thumbnail] 응답에 이미지 데이터 없음")
            return None

        # 이미지 저장
        file_id = str(uuid.uuid4())[:8]
        ext = "png" if "png" in mime_type else "jpg"
        filename = f"{file_id}.{ext}"
        filepath = THUMBNAIL_DIR / filename

        image_bytes = base64.b64decode(image_data)
        filepath.write_bytes(image_bytes)

        logger.info(f"[Thumbnail] 이미지 저장 완료: {filepath} ({len(image_bytes)} bytes)")
        return f"/thumbnails/{filename}"

    except Exception as e:
        logger.error(f"[Thumbnail] 이미지 생성 실패: {e}")
        return None


async def generate_thumbnail_stream(
    topic: str,
    style: str = "impact",
    keywords: list[str] | None = None,
    tone: str | None = None,
    custom_request: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    SSE 스트리밍으로 썸네일 생성 진행 상황 전달.

    Yields:
        SSE 포맷의 JSON 이벤트
    """

    def _sse(data: dict) -> str:
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    # Step 1: 프롬프트 생성
    yield _sse({"step": "prompt", "message": "🎨 프롬프트 생성 중...", "progress": 20})

    prompt = await build_image_prompt(
        topic=topic,
        style=style,
        keywords=keywords,
        tone=tone,
        custom_request=custom_request,
    )

    yield _sse({
        "step": "prompt_done",
        "message": "✅ 프롬프트 생성 완료",
        "prompt": prompt,
        "progress": 40,
    })

    # Step 2: 이미지 생성
    yield _sse({"step": "generating", "message": "🖼️ 이미지 생성 중... (10~30초 소요)", "progress": 60})

    image_path = await generate_thumbnail_image(prompt)

    if image_path:
        yield _sse({
            "step": "done",
            "message": "✅ 썸네일 배경 생성 완료!",
            "image_url": image_path,
            "prompt": prompt,
            "progress": 100,
        })
    else:
        yield _sse({
            "step": "error",
            "message": "❌ 이미지 생성에 실패했습니다. 다시 시도해주세요.",
            "progress": 0,
        })
