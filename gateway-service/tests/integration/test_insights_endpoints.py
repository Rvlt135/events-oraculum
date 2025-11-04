"""Tests for insights API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4


class TestInsightsEndpoints:
    """Tests for insights endpoints."""

    def test_get_recommendations_without_api_key(self, test_client: TestClient):
        """Test get recommendations without API key."""
        response = test_client.get("/v1/insights/recommendations")
        
        assert response.status_code == 401

    def test_get_recommendations_with_invalid_api_key(self, test_client: TestClient):
        """Test get recommendations with invalid API key."""
        response = test_client.get(
            "/v1/insights/recommendations",
            headers={"X-API-Key": "invalid_key"}
        )
        
        assert response.status_code == 401

    @patch("app.routes.insights.get_session")
    @patch("app.routes.insights.verify_api_key")
    def test_get_recommendations_success(self, mock_verify_api_key, mock_get_session, test_client: TestClient):
        """Test get recommendations success."""
        mock_verify_api_key.return_value = "valid_api_key"
        mock_session = AsyncMock()
        mock_get_session.return_value = mock_session
        
        # Mock repositories and service
        with patch("app.routes.insights.RecommendationsReadRepo") as mock_repo_class, \
             patch("app.routes.insights.EventsReadRepo") as mock_events_repo_class, \
             patch("app.routes.insights.InsightsService") as mock_service_class:
            
            mock_repo = AsyncMock()
            mock_events_repo = AsyncMock()
            mock_service = AsyncMock()
            
            mock_repo_class.return_value = mock_repo
            mock_events_repo_class.return_value = mock_events_repo
            mock_service_class.return_value = mock_service
            
            # Mock service response
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
            
            mock_service.get_recommendations.return_value = ([mock_recommendation], 1)
            
            response = test_client.get(
                "/v1/insights/recommendations",
                headers={"X-API-Key": "valid_api_key"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "total" in data
            assert "limit" in data
            assert "offset" in data
            assert "items" in data
            assert data["total"] == 1
            assert len(data["items"]) == 1

    @patch("app.routes.insights.get_session")
    @patch("app.routes.insights.verify_api_key")
    def test_get_recommendations_with_filters(self, mock_verify_api_key, mock_get_session, test_client: TestClient):
        """Test get recommendations with filters."""
        mock_verify_api_key.return_value = "valid_api_key"
        mock_session = AsyncMock()
        mock_get_session.return_value = mock_session
        
        with patch("app.routes.insights.RecommendationsReadRepo") as mock_repo_class, \
             patch("app.routes.insights.EventsReadRepo") as mock_events_repo_class, \
             patch("app.routes.insights.InsightsService") as mock_service_class:
            
            mock_repo = AsyncMock()
            mock_events_repo = AsyncMock()
            mock_service = AsyncMock()
            
            mock_repo_class.return_value = mock_repo
            mock_events_repo_class.return_value = mock_events_repo
            mock_service_class.return_value = mock_service
            
            mock_service.get_recommendations.return_value = ([], 0)
            
            response = test_client.get(
                "/v1/insights/recommendations?league=Premier%20League&min_conf=0.7&limit=10&offset=0",
                headers={"X-API-Key": "valid_api_key"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert data["limit"] == 10
            assert data["offset"] == 0

    def test_get_event_details_without_api_key(self, test_client: TestClient):
        """Test get event details without API key."""
        event_id = str(uuid4())
        response = test_client.get(f"/v1/insights/events/{event_id}")
        
        assert response.status_code == 401

    @patch("app.routes.insights.get_session")
    @patch("app.routes.insights.verify_api_key")
    def test_get_event_details_success(self, mock_verify_api_key, mock_get_session, test_client: TestClient):
        """Test get event details success."""
        mock_verify_api_key.return_value = "valid_api_key"
        mock_session = AsyncMock()
        mock_get_session.return_value = mock_session
        
        with patch("app.routes.insights.RecommendationsReadRepo") as mock_repo_class, \
             patch("app.routes.insights.EventsReadRepo") as mock_events_repo_class, \
             patch("app.routes.insights.InsightsService") as mock_service_class:
            
            mock_repo = AsyncMock()
            mock_events_repo = AsyncMock()
            mock_service = AsyncMock()
            
            mock_repo_class.return_value = mock_repo
            mock_events_repo_class.return_value = mock_events_repo
            mock_service_class.return_value = mock_service
            
            # Mock service response
            mock_event = MagicMock()
            mock_event.model_dump.return_value = {
                "id": str(uuid4()),
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
            
            mock_service.get_event_details.return_value = mock_event
            
            event_id = str(uuid4())
            response = test_client.get(
                f"/v1/insights/events/{event_id}",
                headers={"X-API-Key": "valid_api_key"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["league"] == "Premier League"
            assert data["home_team"] == "Manchester United"
            assert data["away_team"] == "Liverpool"

    @patch("app.routes.insights.get_session")
    @patch("app.routes.insights.verify_api_key")
    def test_get_event_details_not_found(self, mock_verify_api_key, mock_get_session, test_client: TestClient):
        """Test get event details not found."""
        mock_verify_api_key.return_value = "valid_api_key"
        mock_session = AsyncMock()
        mock_get_session.return_value = mock_session
        
        with patch("app.routes.insights.RecommendationsReadRepo") as mock_repo_class, \
             patch("app.routes.insights.EventsReadRepo") as mock_events_repo_class, \
             patch("app.routes.insights.InsightsService") as mock_service_class:
            
            mock_repo = AsyncMock()
            mock_events_repo = AsyncMock()
            mock_service = AsyncMock()
            
            mock_repo_class.return_value = mock_repo
            mock_events_repo_class.return_value = mock_events_repo
            mock_service_class.return_value = mock_service
            
            mock_service.get_event_details.return_value = None
            
            event_id = str(uuid4())
            response = test_client.get(
                f"/v1/insights/events/{event_id}",
                headers={"X-API-Key": "valid_api_key"}
            )
            
            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"]

    def test_get_recommendations_invalid_parameters(self, test_client: TestClient):
        """Test get recommendations with invalid parameters."""
        response = test_client.get(
            "/v1/insights/recommendations?limit=1000&offset=-1",
            headers={"X-API-Key": "valid_api_key"}
        )
        
        assert response.status_code == 422

    def test_get_recommendations_invalid_confidence(self, test_client: TestClient):
        """Test get recommendations with invalid confidence value."""
        response = test_client.get(
            "/v1/insights/recommendations?min_conf=1.5",
            headers={"X-API-Key": "valid_api_key"}
        )
        
        assert response.status_code == 422
