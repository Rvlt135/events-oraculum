"""Tests for insights service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.insights_service import InsightsService
from app.models.schemas import RecommendationDTO, EventDTO


class TestInsightsService:
    """Tests for InsightsService."""

    @pytest.fixture
    def mock_recommendations_repo(self):
        """Mock recommendations repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_events_repo(self):
        """Mock events repository."""
        return AsyncMock()

    @pytest.fixture
    def insights_service(self, mock_recommendations_repo, mock_events_repo):
        """Create InsightsService instance with mocked dependencies."""
        return InsightsService(mock_recommendations_repo, mock_events_repo)

    @pytest.mark.asyncio
    async def test_get_recommendations_success(self, insights_service, mock_recommendations_repo):
        """Test get recommendations success."""
        # Mock repository response
        mock_recommendation = MagicMock()
        mock_recommendation.model_dump.return_value = {
            "id": str(uuid4()),
            "event_id": str(uuid4()),
            "league": "Premier League",
            "home_team": "Manchester United",
            "away_team": "Liverpool",
            "match_date": "2024-01-15T15:30:00Z",
            "prediction": "home_win",
            "confidence": 0.85,
            "odds": 2.1,
            "recommended_stake": 100.0,
            "expected_value": 0.15,
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        mock_recommendations_repo.get_recommendations.return_value = ([mock_recommendation], 1)
        
        # Test service call
        recommendations, total = await insights_service.get_recommendations(
            league="Premier League",
            min_confidence=0.7,
            limit=10,
            offset=0
        )
        
        assert total == 1
        assert len(recommendations) == 1
        mock_recommendations_repo.get_recommendations.assert_called_once_with(
            league="Premier League",
            min_confidence=0.7,
            limit=10,
            offset=0
        )

    @pytest.mark.asyncio
    async def test_get_recommendations_with_filters(self, insights_service, mock_recommendations_repo):
        """Test get recommendations with various filters."""
        mock_recommendations_repo.get_recommendations.return_value = ([], 0)
        
        await insights_service.get_recommendations(
            league="La Liga",
            min_confidence=0.8,
            limit=5,
            offset=10
        )
        
        mock_recommendations_repo.get_recommendations.assert_called_once_with(
            league="La Liga",
            min_confidence=0.8,
            limit=5,
            offset=10
        )

    @pytest.mark.asyncio
    async def test_get_recommendations_no_filters(self, insights_service, mock_recommendations_repo):
        """Test get recommendations without filters."""
        mock_recommendations_repo.get_recommendations.return_value = ([], 0)
        
        await insights_service.get_recommendations()
        
        mock_recommendations_repo.get_recommendations.assert_called_once_with(
            league=None,
            min_confidence=None,
            limit=50,
            offset=0
        )

    @pytest.mark.asyncio
    @patch("app.services.insights_service.redis_cache_manager")
    async def test_get_event_details_from_cache(self, mock_redis_cache, insights_service, mock_events_repo):
        """Test get event details from cache."""
        event_id = uuid4()
        cache_key = f"event:{event_id}"
        
        # Mock cache hit
        cached_data = {
            "id": str(event_id),
            "league": "Premier League",
            "home_team": "Manchester United",
            "away_team": "Liverpool",
            "match_date": "2024-01-15T15:30:00Z",
            "status": "scheduled",
            "home_score": None,
            "away_score": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
        mock_redis_cache.get.return_value = cached_data
        
        result = await insights_service.get_event_details(event_id)
        
        assert result is not None
        assert result.league == "Premier League"
        mock_redis_cache.get.assert_called_once_with(cache_key)
        mock_events_repo.get_event_details.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.insights_service.redis_cache_manager")
    async def test_get_event_details_from_database(self, mock_redis_cache, insights_service, mock_events_repo):
        """Test get event details from database when not in cache."""
        event_id = uuid4()
        cache_key = f"event:{event_id}"
        
        # Mock cache miss
        mock_redis_cache.get.return_value = None
        
        # Mock database response
        mock_event = MagicMock()
        mock_event.model_dump.return_value = {
            "id": str(event_id),
            "league": "Premier League",
            "home_team": "Manchester United",
            "away_team": "Liverpool",
            "match_date": "2024-01-15T15:30:00Z",
            "status": "scheduled",
            "home_score": None,
            "away_score": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
        
        mock_events_repo.get_event_details.return_value = mock_event
        mock_events_repo.get_recommendations_for_event.return_value = []
        mock_events_repo.get_odds_context.return_value = None
        
        result = await insights_service.get_event_details(event_id)
        
        assert result is not None
        assert result.league == "Premier League"
        mock_redis_cache.get.assert_called_once_with(cache_key)
        mock_events_repo.get_event_details.assert_called_once_with(event_id)
        mock_redis_cache.set.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.insights_service.redis_cache_manager")
    async def test_get_event_details_not_found(self, mock_redis_cache, insights_service, mock_events_repo):
        """Test get event details when event not found."""
        event_id = uuid4()
        
        # Mock cache miss
        mock_redis_cache.get.return_value = None
        
        # Mock database response - event not found
        mock_events_repo.get_event_details.return_value = None
        
        result = await insights_service.get_event_details(event_id)
        
        assert result is None
        mock_events_repo.get_event_details.assert_called_once_with(event_id)
        mock_redis_cache.set.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.insights_service.redis_cache_manager")
    async def test_get_event_details_with_recommendations(self, mock_redis_cache, insights_service, mock_events_repo):
        """Test get event details with recommendations."""
        event_id = uuid4()
        
        # Mock cache miss
        mock_redis_cache.get.return_value = None
        
        # Mock database responses
        mock_event = MagicMock()
        mock_event.model_dump.return_value = {
            "id": str(event_id),
            "league": "Premier League",
            "home_team": "Manchester United",
            "away_team": "Liverpool",
            "match_date": "2024-01-15T15:30:00Z",
            "status": "scheduled",
            "home_score": None,
            "away_score": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
        
        mock_recommendation = MagicMock()
        mock_recommendation.model_dump.return_value = {
            "id": str(uuid4()),
            "event_id": str(event_id),
            "league": "Premier League",
            "home_team": "Manchester United",
            "away_team": "Liverpool",
            "match_date": "2024-01-15T15:30:00Z",
            "prediction": "home_win",
            "confidence": 0.85,
            "odds": 2.1,
            "recommended_stake": 100.0,
            "expected_value": 0.15,
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        mock_odds_context = MagicMock()
        mock_odds_context.model_dump.return_value = {
            "home_odds": 2.1,
            "draw_odds": 3.2,
            "away_odds": 3.5,
            "bookmaker": "Bet365"
        }
        
        mock_events_repo.get_event_details.return_value = mock_event
        mock_events_repo.get_recommendations_for_event.return_value = [mock_recommendation]
        mock_events_repo.get_odds_context.return_value = mock_odds_context
        
        result = await insights_service.get_event_details(event_id)
        
        assert result is not None
        assert result.league == "Premier League"
        mock_events_repo.get_recommendations_for_event.assert_called_once_with(event_id)
        mock_events_repo.get_odds_context.assert_called_once_with(event_id)

    @pytest.mark.asyncio
    async def test_get_recommendations_repository_error(self, insights_service, mock_recommendations_repo):
        """Test get recommendations when repository raises error."""
        mock_recommendations_repo.get_recommendations.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            await insights_service.get_recommendations()

    @pytest.mark.asyncio
    @patch("app.services.insights_service.redis_cache_manager")
    async def test_get_event_details_cache_error(self, mock_redis_cache, insights_service, mock_events_repo):
        """Test get event details when cache raises error."""
        event_id = uuid4()
        
        # Mock cache error
        mock_redis_cache.get.side_effect = Exception("Redis error")
        
        # Should still work by falling back to database
        mock_event = MagicMock()
        mock_event.model_dump.return_value = {
            "id": str(event_id),
            "league": "Premier League",
            "home_team": "Manchester United",
            "away_team": "Liverpool",
            "match_date": "2024-01-15T15:30:00Z",
            "status": "scheduled",
            "home_score": None,
            "away_score": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
        
        mock_events_repo.get_event_details.return_value = mock_event
        mock_events_repo.get_recommendations_for_event.return_value = []
        mock_events_repo.get_odds_context.return_value = None
        
        result = await insights_service.get_event_details(event_id)
        
        assert result is not None
        assert result.league == "Premier League"
