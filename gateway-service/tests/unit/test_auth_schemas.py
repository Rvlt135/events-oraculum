"""Tests for authentication schemas."""

import pytest
from datetime import datetime
from uuid import uuid4
from app.api.schemas.user import  UserProfile, TelegramInfo, AuthResponse, MeResponse
from app.api.schemas.auth import AuthTokens, EmailRegisterRequest, EmailLoginRequest, TokenRefreshRequest

class TestTelegramInfo:
    """Tests for TelegramInfo schema."""

    def test_telegram_info_minimal(self):
        """Test TelegramInfo with minimal required fields."""
        telegram_info = TelegramInfo(account_id=123456789)
        
        assert telegram_info.account_id == 123456789
        assert telegram_info.username is None
        assert telegram_info.first_name is None
        assert telegram_info.last_name is None
        assert telegram_info.language_code is None
        assert telegram_info.photo_url is None
        assert telegram_info.is_premium is False

    def test_telegram_info_full(self, sample_telegram_data):
        """Test TelegramInfo with all fields."""
        telegram_info = TelegramInfo(**sample_telegram_data)
        
        assert telegram_info.account_id == sample_telegram_data["account_id"]
        assert telegram_info.username == sample_telegram_data["username"]
        assert telegram_info.first_name == sample_telegram_data["first_name"]
        assert telegram_info.last_name == sample_telegram_data["last_name"]
        assert telegram_info.language_code == sample_telegram_data["language_code"]
        assert telegram_info.photo_url == sample_telegram_data["photo_url"]
        assert telegram_info.is_premium == sample_telegram_data["is_premium"]

    def test_telegram_info_validation(self):
        """Test TelegramInfo validation."""
        # Valid data
        valid_data = {
            "account_id": 123456789,
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "language_code": "en",
            "photo_url": "https://t.me/i/userpic/320/testuser.jpg",
            "is_premium": True,
        }
        telegram_info = TelegramInfo(**valid_data)
        assert telegram_info.account_id == 123456789

        # Invalid account_id (should be int)
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            TelegramInfo(account_id="invalid")

    def test_telegram_info_serialization(self, sample_telegram_data):
        """Test TelegramInfo serialization."""
        telegram_info = TelegramInfo(**sample_telegram_data)
        data = telegram_info.model_dump()
        
        assert data["account_id"] == sample_telegram_data["account_id"]
        assert data["username"] == sample_telegram_data["username"]
        assert data["is_premium"] == sample_telegram_data["is_premium"]


class TestUserProfile:
    """Tests for UserProfile schema."""

    def test_user_profile_without_telegram(self, sample_user_data):
        """Test UserProfile without Telegram info."""
        user_profile = UserProfile(**sample_user_data)
        
        assert str(user_profile.id) == sample_user_data["id"]
        assert user_profile.email == sample_user_data["email"]
        assert user_profile.email_verified == sample_user_data["email_verified"]
        assert user_profile.plan_type == sample_user_data["plan_type"]
        assert user_profile.telegram is None

    def test_user_profile_with_telegram(self, sample_user_data, sample_telegram_data):
        """Test UserProfile with Telegram info."""
        telegram_info = TelegramInfo(**sample_telegram_data)
        user_profile = UserProfile(
            **sample_user_data,
            telegram=telegram_info
        )
        
        assert str(user_profile.id) == sample_user_data["id"]
        assert user_profile.email == sample_user_data["email"]
        assert user_profile.telegram is not None
        assert user_profile.telegram.account_id == sample_telegram_data["account_id"]
        assert user_profile.telegram.username == sample_telegram_data["username"]

    def test_user_profile_validation(self):
        """Test UserProfile validation."""
        # Valid data
        valid_data = {
            "id": uuid4(),
            "email": "test@example.com",
            "email_verified": True,
            "plan_type": "free",
            "trial_end_at": None,
            "created_at": datetime.utcnow(),
        }
        user_profile = UserProfile(**valid_data)
        assert user_profile.email == "test@example.com"

        # Test with different email format (UserProfile accepts any string)
        user_profile_invalid_email = UserProfile(
            id=uuid4(),
            email="invalid-email",
            email_verified=True,
            plan_type="free",
            trial_end_at=None,
            created_at=datetime.utcnow(),
        )
        assert user_profile_invalid_email.email == "invalid-email"


class TestAuthTokens:
    """Tests for AuthTokens schema."""

    def test_auth_tokens_creation(self):
        """Test AuthTokens creation."""
        tokens = AuthTokens(
            access_token="access_token_123",
            refresh_token="refresh_token_456"
        )
        
        assert tokens.access_token == "access_token_123"
        assert tokens.refresh_token == "refresh_token_456"
        assert tokens.token_type == "bearer"

    def test_auth_tokens_with_custom_type(self):
        """Test AuthTokens with custom token type."""
        tokens = AuthTokens(
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            token_type="custom"
        )
        
        assert tokens.token_type == "custom"


class TestAuthResponse:
    """Tests for AuthResponse schema."""

    def test_auth_response_creation(self, sample_user_data, sample_telegram_data):
        """Test AuthResponse creation."""
        user_profile = UserProfile(**sample_user_data)
        tokens = AuthTokens(
            access_token="access_token_123",
            refresh_token="refresh_token_456"
        )
        
        auth_response = AuthResponse(user=user_profile, tokens=tokens)
        
        assert auth_response.user == user_profile
        assert auth_response.tokens == tokens


class TestEmailRequests:
    """Tests for email request schemas."""

    def test_email_register_request(self):
        """Test EmailRegisterRequest validation."""
        # Valid request
        request = EmailRegisterRequest(
            email="test@example.com",
            password="password123"
        )
        assert request.email == "test@example.com"
        assert request.password == "password123"

        # Invalid email
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            EmailRegisterRequest(
                email="invalid-email",
                password="password123"
            )

        # Password too short
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            EmailRegisterRequest(
                email="test@example.com",
                password="123"
            )

    def test_email_login_request(self):
        """Test EmailLoginRequest validation."""
        request = EmailLoginRequest(
            email="test@example.com",
            password="password123"
        )
        assert request.email == "test@example.com"
        assert request.password == "password123"


class TestTokenRefreshRequest:
    """Tests for TokenRefreshRequest schema."""

    def test_token_refresh_request(self):
        """Test TokenRefreshRequest creation."""
        request = TokenRefreshRequest(refresh_token="refresh_token_123")
        assert request.refresh_token == "refresh_token_123"


class TestMeResponse:
    """Tests for MeResponse schema."""

    def test_me_response_creation(self, sample_user_data):
        """Test MeResponse creation."""
        user_profile = UserProfile(**sample_user_data)
        me_response = MeResponse(
            user=user_profile,
            trial_left_days=30,
            is_trial_active=True
        )
        
        assert me_response.user == user_profile
        assert me_response.trial_left_days == 30
        assert me_response.is_trial_active is True

    def test_me_response_without_trial(self, sample_user_data):
        """Test MeResponse without trial."""
        user_profile = UserProfile(**sample_user_data)
        me_response = MeResponse(
            user=user_profile,
            trial_left_days=None,
            is_trial_active=False
        )
        
        assert me_response.trial_left_days is None
        assert me_response.is_trial_active is False
