"""Tests for Redis cache."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

from app.cache.redis import RedisCache


class TestRedisCache:
    """Tests for RedisCache."""

    @pytest.fixture
    def redis_cache(self):
        """Create RedisCache instance."""
        return RedisCache()

    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_initialize_success(self, redis_cache, mock_redis_client):
        """Test successful initialization."""
        with patch("app.cache.redis.redis.from_url", return_value=mock_redis_client):
            await redis_cache.initialize()
            
            assert redis_cache.client == mock_redis_client

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, redis_cache, mock_redis_client):
        """Test initialization when already initialized."""
        redis_cache.client = mock_redis_client
        
        with patch("app.cache.redis.redis.from_url") as mock_from_url:
            await redis_cache.initialize()
            
            mock_from_url.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispose_success(self, redis_cache, mock_redis_client):
        """Test successful disposal."""
        redis_cache.client = mock_redis_client
        
        await redis_cache.dispose()
        
        mock_redis_client.close.assert_called_once()
        assert redis_cache.client is None

    @pytest.mark.asyncio
    async def test_dispose_no_client(self, redis_cache):
        """Test disposal when no client."""
        redis_cache.client = None
        
        await redis_cache.dispose()
        
        # Should not raise error
        assert redis_cache.client is None

    @pytest.mark.asyncio
    async def test_get_success(self, redis_cache, mock_redis_client):
        """Test successful get operation."""
        redis_cache.client = mock_redis_client
        
        test_data = {"key": "value", "number": 123}
        mock_redis_client.get.return_value = json.dumps(test_data)
        
        result = await redis_cache.get("test_key")
        
        assert result == test_data
        mock_redis_client.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_cache_miss(self, redis_cache, mock_redis_client):
        """Test get operation with cache miss."""
        redis_cache.client = mock_redis_client
        mock_redis_client.get.return_value = None
        
        result = await redis_cache.get("test_key")
        
        assert result is None
        mock_redis_client.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_not_initialized(self, redis_cache):
        """Test get operation when not initialized."""
        redis_cache.client = None
        
        with pytest.raises(RuntimeError, match="Redis not initialized"):
            await redis_cache.get("test_key")

    @pytest.mark.asyncio
    async def test_get_json_error(self, redis_cache, mock_redis_client):
        """Test get operation with JSON decode error."""
        redis_cache.client = mock_redis_client
        mock_redis_client.get.return_value = "invalid json"
        
        result = await redis_cache.get("test_key")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_redis_error(self, redis_cache, mock_redis_client):
        """Test get operation with Redis error."""
        redis_cache.client = mock_redis_client
        mock_redis_client.get.side_effect = Exception("Redis connection error")
        
        result = await redis_cache.get("test_key")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_set_success(self, redis_cache, mock_redis_client):
        """Test successful set operation."""
        redis_cache.client = mock_redis_client
        redis_cache.ttl = 300
        
        test_data = {"key": "value", "number": 123}
        
        await redis_cache.set("test_key", test_data)
        
        mock_redis_client.set.assert_called_once_with(
            "test_key",
            json.dumps(test_data),
            ex=300
        )

    @pytest.mark.asyncio
    async def test_set_with_custom_ttl(self, redis_cache, mock_redis_client):
        """Test set operation with custom TTL."""
        redis_cache.client = mock_redis_client
        
        test_data = {"key": "value"}
        
        await redis_cache.set("test_key", test_data, ttl=600)
        
        mock_redis_client.set.assert_called_once_with(
            "test_key",
            json.dumps(test_data),
            ex=600
        )

    @pytest.mark.asyncio
    async def test_set_not_initialized(self, redis_cache):
        """Test set operation when not initialized."""
        redis_cache.client = None
        
        with pytest.raises(RuntimeError, match="Redis not initialized"):
            await redis_cache.set("test_key", {"key": "value"})

    @pytest.mark.asyncio
    async def test_set_redis_error(self, redis_cache, mock_redis_client):
        """Test set operation with Redis error."""
        redis_cache.client = mock_redis_client
        mock_redis_client.set.side_effect = Exception("Redis connection error")
        
        # Should not raise error, just log it
        await redis_cache.set("test_key", {"key": "value"})

    @pytest.mark.asyncio
    async def test_delete_success(self, redis_cache, mock_redis_client):
        """Test successful delete operation."""
        redis_cache.client = mock_redis_client
        
        await redis_cache.delete("test_key")
        
        mock_redis_client.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_delete_not_initialized(self, redis_cache):
        """Test delete operation when not initialized."""
        redis_cache.client = None
        
        with pytest.raises(RuntimeError, match="Redis not initialized"):
            await redis_cache.delete("test_key")

    @pytest.mark.asyncio
    async def test_delete_redis_error(self, redis_cache, mock_redis_client):
        """Test delete operation with Redis error."""
        redis_cache.client = mock_redis_client
        mock_redis_client.delete.side_effect = Exception("Redis connection error")
        
        # Should not raise error, just log it
        await redis_cache.delete("test_key")

    @pytest.mark.asyncio
    async def test_set_with_none_ttl(self, redis_cache, mock_redis_client):
        """Test set operation with None TTL."""
        redis_cache.client = mock_redis_client
        redis_cache.ttl = 300
        
        test_data = {"key": "value"}
        
        await redis_cache.set("test_key", test_data, ttl=None)
        
        mock_redis_client.set.assert_called_once_with(
            "test_key",
            json.dumps(test_data),
            ex=300  # Should use default TTL
        )

    @pytest.mark.asyncio
    async def test_set_with_zero_ttl(self, redis_cache, mock_redis_client):
        """Test set operation with zero TTL."""
        redis_cache.client = mock_redis_client
        
        test_data = {"key": "value"}
        
        await redis_cache.set("test_key", test_data, ttl=0)
        
        mock_redis_client.set.assert_called_once_with(
            "test_key",
            json.dumps(test_data),
            ex=0
        )

    def test_redis_cache_initialization(self):
        """Test RedisCache initialization."""
        cache = RedisCache()
        
        assert cache.client is None
        assert cache.ttl == 300  # Default TTL from settings

    def test_redis_cache_with_custom_ttl(self):
        """Test RedisCache with custom TTL."""
        cache = RedisCache()
        cache.ttl = 600
        
        assert cache.ttl == 600
