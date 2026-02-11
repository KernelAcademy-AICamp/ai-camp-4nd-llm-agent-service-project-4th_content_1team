"""
Gemini API 공통 클라이언트.

429 에러 시 프록시 로테이션으로 즉시 재시도.
"""
import logging
import re
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_proxy_rr_idx: int = 0


def _get_proxy_pool() -> list[str]:
    """ENV에서 프록시 풀 파싱 (youtube_proxy_url 재사용)."""
    raw = (settings.youtube_proxy_url or "").strip()
    if not raw:
        return []
    return [p.strip() for p in re.split(r"[,\n;]+", raw) if p.strip()]


def _pick_proxy() -> Optional[str]:
    """라운드로빈으로 프록시 선택."""
    global _proxy_rr_idx
    pool = _get_proxy_pool()
    if not pool:
        return None
    picked = pool[_proxy_rr_idx % len(pool)]
    _proxy_rr_idx += 1
    return picked


def _redact(proxy_url: str) -> str:
    return re.sub(r"(https?://[^:]+):[^@]+@", r"\1:***@", proxy_url)


async def call_gemini(
    prompt: str,
    *,
    temperature: float = 0.3,
    max_output_tokens: int = 8192,
    timeout: float = 120.0,
    max_retries: int = 4,
) -> Optional[str]:
    """
    Gemini API 호출 (프록시 로테이션 포함).

    429 발생 시:
      1) 프록시 풀이 있으면 → 다음 프록시로 즉시 재시도
      2) 프록시 소진 시 → 짧은 대기 후 직접 연결 재시도

    Returns:
        응답 텍스트 (candidates[0].content.parts[0].text) 또는 None
    """
    api_key = settings.gemini_api_key
    if not api_key:
        logger.error("[Gemini] API 키 없음")
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": "application/json",
        },
    }

    proxy_pool = _get_proxy_pool()
    last_error = None

    for attempt in range(max_retries):
        # 첫 시도는 직접 연결, 429 이후에는 프록시 사용
        proxy = None
        if attempt > 0 and proxy_pool:
            proxy = _pick_proxy()

        try:
            transport = httpx.AsyncHTTPTransport(proxy=proxy) if proxy else None
            async with httpx.AsyncClient(
                timeout=timeout,
                transport=transport,
            ) as client:
                resp = await client.post(url, json=body)

            if resp.status_code == 429:
                last_error = "429 Too Many Requests"
                if proxy_pool and attempt < len(proxy_pool):
                    # 프록시가 남아있으면 즉시 다음 프록시로 재시도
                    logger.warning(
                        f"[Gemini] 429 → 프록시 전환 재시도 "
                        f"({attempt+1}/{max_retries}, "
                        f"proxy={_redact(proxy) if proxy else 'direct'})"
                    )
                    continue
                else:
                    # 프록시 소진, 짧은 대기 후 직접 연결 재시도
                    import asyncio
                    wait = (attempt + 1) * 5
                    logger.warning(
                        f"[Gemini] 429 → {wait}초 대기 후 재시도 "
                        f"({attempt+1}/{max_retries})"
                    )
                    await asyncio.sleep(wait)
                    continue

            if resp.status_code != 200:
                last_error = f"HTTP {resp.status_code}"
                logger.error(f"[Gemini] API 에러: {resp.status_code} {resp.text[:200]}")
                continue

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                last_error = "No candidates"
                logger.error("[Gemini] 응답에 candidates 없음")
                continue

            return candidates[0]["content"]["parts"][0]["text"]

        except Exception as e:
            last_error = str(e)
            logger.error(f"[Gemini] 요청 예외 (attempt={attempt+1}): {e}")
            continue

    logger.error(f"[Gemini] {max_retries}회 시도 실패. last_error={last_error}")
    return None
