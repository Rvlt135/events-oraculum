"""Tests for stats API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock


class TestStatsEndpoints:
    """Tests for stats endpoints."""

    def test_get_stats_without_api_key(self, test_client: TestClient):
        """Test get stats without API key."""
        response = test_client.get("/v1/stats/summary")
        
        assert response.status_code == 401

    def test_get_stats_with_invalid_api_key(self, test_client: TestClient):
        """Test get stats with invalid API key."""
        response = test_client.get(
            "/v1/stats/summary",
            headers={"X-API-Key": "invalid_key"}
        )
        
        assert response.status_code == 401

    @patch("app.routes.stats.get_session")
    @patch("app.routes.stats.verify_api_key")
    def test_get_stats_success(self, mock_verify_api_key, mock_get_session, test_client: TestClient):
        """Test get stats success."""
        mock_verify_api_key.return_value = "valid_api_key"
        mock_session = AsyncMock()
        mock_get_session.return_value = mock_session
        
        with patch("app.routes.stats.RecommendationsReadRepo") as mock_repo_class, \
             patch("app.routes.stats.StatsService") as mock_service_class:
            
            mock_repo = AsyncMock()
            mock_service = AsyncMock()
            
            mock_repo_class.return_value = mock_repo
            mock_service_class.return_value = mock_service
            
            # Mock service response
            mock_stats = MagicMock()
            mock_stats.model_dump.return_value = {
                "total_recommendations": 150,
                "successful_predictions": 120,
                "success_rate": 0.8,
                "total_events": 100,
                "completed_events": 95,
                "average_confidence": 0.75,
                "total_stake": 15000.0,
                "total_profit": 2500.0,
                "roi": 0.167,
                "period": {
                    "from": "2024-01-01T00:00:00Z",
                    "to": "2024-01-31T23:59:59Z"
                }
            }
            
            mock_service.get_summary.return_value = mock_stats
            
            response = test_client.get(
                "/v1/stats/summary",
                headers={"X-API-Key": "valid_api_key"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_recommendations"] == 150
            assert data["successful_predictions"] == 120
            assert data["success_rate"] == 0.8
            assert data["total_events"] == 100
            assert data["completed_events"] == 95
            assert data["average_confidence"] == 0.75
            assert data["total_stake"] == 15000.0
            assert data["total_profit"] == 2500.0
            assert data["roi"] == 0.167

    @patch("app.routes.stats.get_session")
    @patch("app.routes.stats.verify_api_key")
    def test_get_stats_with_filters(self, mock_verify_api_key, mock_get_session, test_client: TestClient):
        """Test get stats with filters."""
        mock_verify_api_key.return_value = "valid_api_key"
        mock_session = AsyncMock()
        mock_get_session.return_value = mock_session
        
        with patch("app.routes.stats.RecommendationsReadRepo") as mock_repo_class, \
             patch("app.routes.stats.StatsService") as mock_service_class:
            
            mock_repo = AsyncMock()
            mock_service = AsyncMock()
            
            mock_repo_class.return_value = mock_repo
            mock_service_class.return_value = mock_service
            
            mock_stats = MagicMock()
            mock_stats.model_dump.return_value = {
                "total_recommendations": 50,
                "successful_predictions": 40,
                "success_rate": 0.8,
                "total_events": 30,
                "completed_events": 25,
                "average_confidence": 0.75,
                "total_stake": 5000.0,
                "total_profit": 1000.0,
                "roi": 0.2,
                "period": {
                    "from": "2024-01-01T00:00:00Z",
                    "to": "2024-01-15T23:59:59Z"
                }
            }
            
            mock_service.get_summary.return_value = mock_stats
            
            response = test_client.get(
                "/v1/stats/summary?league=Premier%20League&from=2024-01-01T00:00:00Z&to=2024-01-15T23:59:59Z",
                headers={"X-API-Key": "valid_api_key"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_recommendations"] == 50
            assert data["success_rate"] == 0.8

    @patch("app.routes.stats.get_session")
    @patch("app.routes.stats.verify_api_key")
    def test_get_stats_empty_data(self, mock_verify_api_key, mock_get_session, test_client: TestClient):
        """Test get stats with empty data."""
        mock_verify_api_key.return_value = "valid_api_key"
        mock_session = AsyncMock()
        mock_get_session.return_value = mock_session
        
        with patch("app.routes.stats.RecommendationsReadRepo") as mock_repo_class, \
             patch("app.routes.stats.StatsService") as mock_service_class:
            
            mock_repo = AsyncMock()
            mock_service = AsyncMock()
            
            mock_repo_class.return_value = mock_repo
            mock_service_class.return_value = mock_service
            
            mock_stats = MagicMock()
            mock_stats.model_dump.return_value = {
                "total_recommendations": 0,
                "successful_predictions": 0,
                "success_rate": 0.0,
                "total_events": 0,
                "completed_events": 0,
                "average_confidence": 0.0,
                "total_stake": 0.0,
                "total_profit": 0.0,
                "roi": 0.0,
                "period": {
                    "from": None,
                    "to": None
                }
            }
            
            mock_service.get_summary.return_value = mock_stats
            
            response = test_client.get(
                "/v1/stats/summary",
                headers={"X-API-Key": "valid_api_key"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_recommendations"] == 0
            assert data["success_rate"] == 0.0
            assert data["roi"] == 0.0

    def test_get_stats_invalid_date_format(self, test_client: TestClient):
        """Test get stats with invalid date format."""
        response = test_client.get(
            "/v1/stats/summary?from=invalid-date",
            headers={"X-API-Key": "valid_api_key"}
        )
        
        assert response.status_code == 422
