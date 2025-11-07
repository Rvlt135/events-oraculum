"""Tests for authentication API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.api.schemas.auth import AuthTokens
from app.api.schemas.user import  UserProfile, TelegramInfo

class TestAuthEndpoints:
    """Tests for authentication endpoints."""

    def test_root_endpoint(self, test_client: TestClient):
        """Test root endpoint."""
        response = test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "test-gateway-service"
        assert data["status"] == "running"
        assert data["environment"] == "test"

    def test_health_endpoint(self, test_client: TestClient):
        """Test health endpoint."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_metrics_endpoint(self, test_client: TestClient):
        """Test metrics endpoint."""
        response = test_client.get("/metrics")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"

    @patch("app.routes.auth.get_auth_service")
    def test_google_oauth_start(self, mock_get_auth_service, test_client: TestClient):
        """Test Google OAuth start endpoint."""
        mock_auth_service = AsyncMock()
        mock_google_oauth = AsyncMock()
        mock_google_oauth.get_authorization_url.return_value = "https://accounts.google.com/oauth/authorize"
        mock_auth_service.google = mock_google_oauth
        mock_get_auth_service.return_value = mock_auth_service
        
        response = test_client.get("/auth/google/start")
        
        assert response.status_code == 302
        assert "accounts.google.com" in response.headers["location"]

    @patch("app.routes.auth.get_auth_service")
    def test_google_oauth_callback_success(self, mock_get_auth_service, test_client: TestClient):
        """Test Google OAuth callback success."""
        mock_auth_service = AsyncMock()
        mock_user = AsyncMock()
        mock_user.id = "123e4567-e89b-12d3-a456-426614174000"
        mock_user.email = "test@example.com"
        mock_user.email_verified = True
        mock_user.plan_type = "free"
        mock_user.trial_end_at = None
        mock_user.created_at = "2024-01-01T00:00:00Z"
        mock_user.identities = []
        
        mock_auth_service.login_with_google.return_value = (
            mock_user,
            "access_token",
            "refresh_token"
        )
        mock_get_auth_service.return_value = mock_auth_service
        
        response = test_client.get("/auth/google/callback?code=test_code")
        
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "tokens" in data

    @patch("app.routes.auth.get_auth_service")
    def test_google_oauth_callback_error(self, mock_get_auth_service, test_client: TestClient):
        """Test Google OAuth callback error."""
        mock_auth_service = AsyncMock()
        mock_auth_service.login_with_google.side_effect = ValueError("Invalid code")
        mock_get_auth_service.return_value = mock_auth_service
        
        response = test_client.get("/auth/google/callback?code=invalid_code")
        
        assert response.status_code == 401
        data = response.json()
        assert "Invalid code" in data["detail"]

    @patch("app.routes.auth.get_auth_service")
    def test_register_with_email_success(self, mock_get_auth_service, test_client: TestClient):
        """Test email registration success."""
        mock_auth_service = AsyncMock()
        mock_user = AsyncMock()
        mock_user.id = "123e4567-e89b-12d3-a456-426614174000"
        mock_user.email = "test@example.com"
        mock_user.email_verified = False
        mock_user.plan_type = "free"
        mock_user.trial_end_at = None
        mock_user.created_at = "2024-01-01T00:00:00Z"
        mock_user.identities = []
        
        mock_auth_service.register_with_email.return_value = (
            mock_user,
            "access_token",
            "refresh_token"
        )
        mock_get_auth_service.return_value = mock_auth_service
        
        response = test_client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "tokens" in data
        assert data["user"]["email"] == "test@example.com"

    def test_register_with_email_validation_error(self, test_client: TestClient):
        """Test email registration validation error."""
        response = test_client.post(
            "/auth/register",
            json={
                "email": "invalid-email",
                "password": "123"  # Too short
            }
        )
        
        assert response.status_code == 422

    @patch("app.routes.auth.get_auth_service")
    def test_login_with_email_success(self, mock_get_auth_service, test_client: TestClient):
        """Test email login success."""
        mock_auth_service = AsyncMock()
        mock_user = AsyncMock()
        mock_user.id = "123e4567-e89b-12d3-a456-426614174000"
        mock_user.email = "test@example.com"
        mock_user.email_verified = True
        mock_user.plan_type = "free"
        mock_user.trial_end_at = None
        mock_user.created_at = "2024-01-01T00:00:00Z"
        mock_user.identities = []
        
        mock_auth_service.login_with_email.return_value = (
            mock_user,
            "access_token",
            "refresh_token"
        )
        mock_get_auth_service.return_value = mock_auth_service
        
        response = test_client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "tokens" in data

    @patch("app.routes.auth.get_auth_service")
    def test_login_with_telegram_success(self, mock_get_auth_service, test_client: TestClient):
        """Test Telegram login success."""
        mock_auth_service = AsyncMock()
        mock_user = AsyncMock()
        mock_user.id = "123e4567-e89b-12d3-a456-426614174000"
        mock_user.email = None
        mock_user.email_verified = False
        mock_user.plan_type = "free"
        mock_user.trial_end_at = None
        mock_user.created_at = "2024-01-01T00:00:00Z"
        mock_user.telegram_account_id = 123456789
        mock_user.identities = []
        
        mock_auth_service.login_with_telegram.return_value = (
            mock_user,
            "access_token",
            "refresh_token"
        )
        mock_get_auth_service.return_value = mock_auth_service
        
        response = test_client.post(
            "/auth/telegram",
            json={
                "init_data": "test_init_data"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "tokens" in data

    @patch("app.routes.auth.get_auth_service")
    def test_token_refresh_success(self, mock_get_auth_service, test_client: TestClient):
        """Test token refresh success."""
        mock_auth_service = AsyncMock()
        mock_auth_service.refresh_token.return_value = ("new_access_token", "new_refresh_token")
        mock_get_auth_service.return_value = mock_auth_service
        
        response = test_client.post(
            "/auth/token/refresh",
            json={
                "refresh_token": "old_refresh_token"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "new_access_token"
        assert data["refresh_token"] == "new_refresh_token"

    @patch("app.routes.auth.get_auth_service")
    def test_logout_success(self, mock_get_auth_service, test_client: TestClient):
        """Test logout success."""
        mock_auth_service = AsyncMock()
        mock_auth_service.logout.return_value = None
        mock_get_auth_service.return_value = mock_auth_service
        
        response = test_client.post(
            "/auth/logout",
            json={
                "refresh_token": "refresh_token"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logged out successfully"

    @patch("app.routes.auth.get_current_user")
    def test_get_me_success(self, mock_get_current_user, test_client: TestClient):
        """Test get me endpoint success."""
        mock_user = AsyncMock()
        mock_user.id = "123e4567-e89b-12d3-a456-426614174000"
        mock_user.email = "test@example.com"
        mock_user.email_verified = True
        mock_user.plan_type = "free"
        mock_user.trial_end_at = None
        mock_user.created_at = "2024-01-01T00:00:00Z"
        mock_user.identities = []
        
        mock_get_current_user.return_value = mock_user
        
        response = test_client.get("/auth/me")
        
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "trial_left_days" in data
        assert "is_trial_active" in data

    def test_get_me_unauthorized(self, test_client: TestClient):
        """Test get me endpoint without authorization."""
        response = test_client.get("/auth/me")
        
        assert response.status_code == 401
