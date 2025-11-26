from uuid import UUID

from app.infrastructure.cache.redis import RedisCache
from app.infrastructure.db.orm import User

CATALOG_TTL_SEC = 300
KEY_USER_BY_USER_ID = "user:{user_id}"

def _key_user() -> str:
    return KEY_USER_BY_USER_ID  # если появится мультитенанси/планы — добавляй сегменты тут


class UserCache:
    """User cache repository"""

    def __init__(self, redis: RedisCache) -> None:
        self._r = redis

    async def cache_user(self, user: User) -> None:
        # TODO: change User orm to DTO User
        key = _key_user().format(user_id=user.id)
        data = {
            "id": str(user.id),
            "email": user.email,
            "email_verified": user.email_verified,
            "plan_type": user.plan_type.value,
            "trial_end_at": user.trial_end_at.isoformat() if user.trial_end_at else None,
            "created_at": user.created_at.isoformat(),
        }

        await self._r.set(key, data, ttl=300)

    async def get_cached_user(self, user_id: UUID) -> User | None:
        key = f"user:{user_id}"
        data = await self._r.get(key)
        if not data:
            return None
        return None
