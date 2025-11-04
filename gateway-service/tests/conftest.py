"""Pytest configuration and fixtures."""

import asyncio
import os
import sys
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app
from app.config.settings import Settings
from app.domain.auth_models import Base


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Test settings with overridden values."""
    return Settings(
        service_name="test-gateway-service",
        environment="test",
        log_level="DEBUG",
        api_host="127.0.0.1",
        api_port=8080,
        api_key="test_api_key",
        redis_url="redis://localhost:6379/1",  # Use different DB for tests
        postgres_host="localhost",
        postgres_port=5432,
        postgres_user="postgres",
        postgres_password="postgres",
        postgres_db="test_layerbit",
        jwt_secret="test_jwt_secret_min_32_chars_long",
        jwt_algorithm="HS256",
        access_token_ttl_seconds=900,
        refresh_token_ttl_seconds=1209600,
        google_client_id="test_google_client_id",
        google_client_secret="test_google_client_secret",
        google_redirect_uri="http://localhost:8080/auth/google/callback",
        telegram_bot_token="test_telegram_bot_token",
        telegram_max_auth_age_seconds=600,
        cors_origins=["http://localhost:3000"],
        cache_ttl_seconds=300,
        default_page_limit=50,
        max_page_limit=500,
        password_hash_scheme="argon2",
    )


@pytest.fixture
def test_db_url(test_settings: Settings) -> str:
    """Test database URL."""
    return f"postgresql+asyncpg://{test_settings.postgres_user}:{test_settings.postgres_password}@{test_settings.postgres_host}:{test_settings.postgres_port}/{test_settings.postgres_db}"


@pytest.fixture
async def test_engine(test_db_url: str):
    """Test database engine."""
    engine = create_async_engine(test_db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def test_db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Test database session."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = True
    return mock_redis


@pytest.fixture
def test_client(test_settings: Settings, mock_redis) -> TestClient:
    """Test client with mocked dependencies."""
    # Override settings
    app.dependency_overrides = {}
    
    # Mock Redis
    from app.cache.redis import redis_cache_manager
    redis_cache_manager.client = mock_redis
    
    return TestClient(app)


@pytest.fixture
def mock_jwt_service():
    """Mock JWT service."""
    mock_jwt = MagicMock()
    mock_jwt.generate_tokens.return_value = ("access_token", "refresh_token")
    mock_jwt.verify_token.return_value = {"sub": "test_user_id", "type": "access"}
    return mock_jwt


@pytest.fixture
def mock_auth_service():
    """Mock auth service."""
    mock_auth = AsyncMock()
    mock_auth.register_with_email.return_value = (MagicMock(), "access_token", "refresh_token")
    mock_auth.login_with_email.return_value = (MagicMock(), "access_token", "refresh_token")
    mock_auth.login_with_telegram.return_value = (MagicMock(), "access_token", "refresh_token")
    mock_auth.get_user_by_id.return_value = MagicMock()
    return mock_auth


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "email": "test@example.com",
        "email_verified": True,
        "plan_type": "free",
        "trial_end_at": None,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_telegram_data():
    """Sample Telegram data for testing."""
    return {
        "account_id": 123456789,
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "language_code": "en",
        "photo_url": "https://t.me/i/userpic/320/testuser.jpg",
        "is_premium": True,
    }


@pytest.fixture
def sample_recommendation_data():
    """Sample recommendation data for testing."""
    return {
        "id": "456e7890-e89b-12d3-a456-426614174001",
        "event_id": "789e0123-e89b-12d3-a456-426614174002",
        "league": "Premier League",
        "home_team": "Manchester United",
        "away_team": "Liverpool",
        "match_date": "2024-01-15T15:30:00Z",
        "prediction": "home_win",
        "confidence": 0.85,
        "odds": 2.1,
        "recommended_stake": 100.0,
        "expected_value": 0.15,
        "created_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_event_data():
    """Sample event data for testing."""
    return {
        "id": "789e0123-e89b-12d3-a456-426614174002",
        "league": "Premier League",
        "home_team": "Manchester United",
        "away_team": "Liverpool",
        "match_date": "2024-01-15T15:30:00Z",
        "status": "scheduled",
        "home_score": None,
        "away_score": None,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
