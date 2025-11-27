from app.infrastructure.cache.redis import RedisCache

SETTING_KEY = "setting:{key}"

def _key_setting() -> str:
    return SETTING_KEY


class SettingCache:
    """Setting cache repository"""

    def __init__(self, redis: RedisCache) -> None:
        self._r = redis

    async def set_setting_cache(self, key: str, value: str) -> None:
        key = _key_setting().format(key=key)

        await self._r.set(key, value, indefinitely=True)

    # TODO think what will be the default value ("true" is temporary) 
    async def get_setting_cache(self, key: str, default: str = "true") -> str:
        key = _key_setting().format(key=key)
        value = await self._r.get(key)
        if not value:
            await self.set_setting_cache(key, default)
            return default
        return value
