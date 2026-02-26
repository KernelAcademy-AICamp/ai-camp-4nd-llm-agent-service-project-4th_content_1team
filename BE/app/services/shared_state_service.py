"""
SharedStateService — Redis 기반 사용자별 에이전트 공유 상태 관리

채널 프로필(channel_profile)을 Redis에 캐시하여
스크립트 생성 요청마다 DB를 재조회하는 오버헤드를 제거합니다.

키 구조:
    shared_state:channel_profile:{user_id}

TTL:
    1시간 (페르소나 재생성/수정 시 즉시 무효화)

동작 흐름:
    1. GET /personas/channel-profile     → Redis 우선 조회 → MISS 시 DB 조회 후 캐시
    2. POST /personas/generate           → 페르소나 재생성 후 캐시 무효화
    3. PATCH /personas/me                → 페르소나 수정 후 캐시 무효화
    4. build_planner_input (script-gen)  → Redis 우선 조회 → MISS 시 DB 조회 후 캐시
"""

import json
import logging
from typing import Any, Dict, Optional

from app.core.redis import get_redis

logger = logging.getLogger(__name__)

_KEY_PREFIX = "shared_state:channel_profile"
_TTL_SECONDS = 3600  # 1시간


def _key(user_id: str) -> str:
    return f"{_KEY_PREFIX}:{user_id}"


class SharedStateService:

    @staticmethod
    async def get_channel_profile(user_id: str) -> Optional[Dict[str, Any]]:
        """
        Redis에서 channel_profile 조회.
        캐시 미스 또는 Redis 장애 시 None 반환 (fallback to DB).
        """
        try:
            redis = await get_redis()
            raw = await redis.get(_key(user_id))
            if raw:
                logger.debug(f"[SharedState] HIT  channel_profile user={user_id}")
                return json.loads(raw)
            logger.debug(f"[SharedState] MISS channel_profile user={user_id}")
        except Exception as e:
            logger.warning(f"[SharedState] GET 실패 (user={user_id}): {e}")
        return None

    @staticmethod
    async def set_channel_profile(
        user_id: str,
        profile: Dict[str, Any],
        ttl: int = _TTL_SECONDS,
    ) -> None:
        """
        Redis에 channel_profile 저장.
        저장 실패해도 서비스에 영향 없도록 예외를 삼킵니다.
        """
        try:
            redis = await get_redis()
            await redis.setex(
                _key(user_id),
                ttl,
                json.dumps(profile, ensure_ascii=False),
            )
            logger.info(
                f"[SharedState] SET  channel_profile user={user_id} "
                f"ttl={ttl}s keys={list(profile.keys())}"
            )
        except Exception as e:
            logger.warning(f"[SharedState] SET 실패 (user={user_id}): {e}")

    @staticmethod
    async def invalidate_channel_profile(user_id: str) -> None:
        """
        페르소나 재생성/수정 시 캐시 무효화.
        다음 스크립트 생성 요청에서 DB를 재조회하고 새로 캐시합니다.
        """
        try:
            redis = await get_redis()
            deleted = await redis.delete(_key(user_id))
            if deleted:
                logger.info(f"[SharedState] INVALIDATED channel_profile user={user_id}")
            else:
                logger.debug(f"[SharedState] INVALIDATE skip (없음) user={user_id}")
        except Exception as e:
            logger.warning(f"[SharedState] DELETE 실패 (user={user_id}): {e}")
