"""
Async Redis 클라이언트 싱글톤

Celery 브로커와 동일한 Redis를 사용하되,
애플리케이션 레벨 SharedState 캐시 전용 연결을 별도로 관리합니다.
"""

import logging
import inspect
from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """
    애플리케이션 전역 async Redis 클라이언트 반환 (lazy init).
    연결 실패 시 예외를 발생시키지 않고 None을 반환합니다.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info(f"[Redis] 클라이언트 초기화")
    return _redis_client


async def close_redis() -> None:
    """애플리케이션 종료 시 Redis 연결 정리."""
    global _redis_client
    if _redis_client is not None:
        # redis-py 5.x: aclose() (async)
        # redis-py 4.x 이하: close() (sync 또는 async)만 존재할 수 있음
        close_method = getattr(_redis_client, "aclose", None)

        if close_method is None:
            close_method = getattr(_redis_client, "close", None)

        if close_method is not None:
            result = close_method()
            if inspect.isawaitable(result):
                await result

        _redis_client = None
        logger.info("[Redis] 연결 종료")
