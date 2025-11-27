from datetime import UTC, datetime

from app.config.settings import settings
from app.infrastructure.cache.redis import RedisCache

CATALOG_TTL_SEC = 300
KEY_OAUTH_STATE = "oauth:state:{state}"

def _key_oauth() -> str:
    return KEY_OAUTH_STATE  # если появится мультитенанси/планы — добавляй сегменты тут


class OauthCache:
    """Oauth transaction cache repository"""

    def __init__(self, redis: RedisCache) -> None:
        self._r = redis

    async def cache_oauth_transaction(
            self, oauth_params: dict, request_params: dict, ttl: int = 600) -> None:

        transaction = {
            "provider": "GOOGLE",
            "redirect_uri": settings.google_redirect_uri,
            "status": "PENDING",
            "created_at": datetime.now(UTC).isoformat(),
        }

        transaction.update(oauth_params)
        transaction.update(request_params)

        state = transaction.pop("state")
        state_key = _key_oauth().format(state=state)
        await self._r.set(state_key, transaction, ttl=ttl)


    async def get_cached_oauth_transation(self, state: str) -> dict | None:
        key = _key_oauth().format(state=state)
        data = await self._r.get(key)
        if not data:
            return None
        return data

    async def invalidate_transation(self, state: str) -> None:
        key = _key_oauth().format(state=state)
        await self._r.delete(key)
