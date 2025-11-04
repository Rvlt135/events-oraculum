"""Simple tests for JWT utilities."""

import pytest
from uuid import uuid4, UUID

from app.auth.jwt_utils import JWTService


class TestJWTServiceSimple:
    """Simple tests for JWTService."""

    @pytest.fixture
    def jwt_service(self):
        """Create JWTService instance with longer TTL."""
        return JWTService(
            secret="test_secret_key_min_32_chars_long",
            algorithm="HS256",
            access_ttl=3600,  # 1 hour
            refresh_ttl=86400  # 1 day
        )

    def test_jwt_service_initialization(self):
        """Test JWTService initialization."""
        service = JWTService(
            secret="test_secret",
            algorithm="HS256",
            access_ttl=300,
            refresh_ttl=3600
        )
        
        assert service.secret == "test_secret"
        assert service.algorithm == "HS256"
        assert service.access_ttl == 300
        assert service.refresh_ttl == 3600

    def test_create_access_token(self, jwt_service):
        """Test access token creation."""
        user_id = uuid4()
        access_token = jwt_service.create_access_token(user_id, "free")
        
        assert isinstance(access_token, str)
        assert len(access_token) > 0
        assert access_token.count(".") == 2  # JWT format

    def test_create_refresh_token(self, jwt_service):
        """Test refresh token creation."""
        user_id = uuid4()
        refresh_token, jti = jwt_service.create_refresh_token(user_id)
        
        assert isinstance(refresh_token, str)
        assert isinstance(jti, UUID)
        assert len(refresh_token) > 0
        assert refresh_token.count(".") == 2  # JWT format

    def test_verify_access_token(self, jwt_service):
        """Test access token verification."""
        user_id = uuid4()
        access_token = jwt_service.create_access_token(user_id, "free")
        
        payload = jwt_service.verify_token(access_token, expected_type="access")
        
        assert payload.sub == str(user_id)
        assert payload.type == "access"
        assert payload.plan == "free"
        assert payload.exp > 0
        assert payload.iat > 0

    def test_verify_refresh_token(self, jwt_service):
        """Test refresh token verification."""
        user_id = uuid4()
        refresh_token, jti = jwt_service.create_refresh_token(user_id)
        
        payload = jwt_service.verify_token(refresh_token, expected_type="refresh")
        
        assert payload.sub == str(user_id)
        assert payload.type == "refresh"
        assert payload.jti == str(jti)
        assert payload.exp > 0
        assert payload.iat > 0

    def test_verify_token_wrong_type(self, jwt_service):
        """Test token verification with wrong type."""
        user_id = uuid4()
        access_token = jwt_service.create_access_token(user_id, "free")
        
        with pytest.raises(ValueError, match="Invalid token type"):
            jwt_service.verify_token(access_token, expected_type="refresh")

    def test_verify_invalid_token(self, jwt_service):
        """Test verification of invalid token."""
        with pytest.raises(ValueError, match="Invalid token"):
            jwt_service.verify_token("invalid_token", expected_type="access")

    def test_token_uniqueness(self, jwt_service):
        """Test that tokens are unique for each generation."""
        user_id = uuid4()
        
        access1 = jwt_service.create_access_token(user_id, "free")
        access2 = jwt_service.create_access_token(user_id, "free")
        refresh1, _ = jwt_service.create_refresh_token(user_id)
        refresh2, _ = jwt_service.create_refresh_token(user_id)
        
        # Each generation should produce different tokens
        assert access1 != access2
        assert refresh1 != refresh2

    def test_different_users_different_tokens(self, jwt_service):
        """Test that different users get different tokens."""
        user1_id = uuid4()
        user2_id = uuid4()
        
        access1 = jwt_service.create_access_token(user1_id, "free")
        access2 = jwt_service.create_access_token(user2_id, "free")
        refresh1, _ = jwt_service.create_refresh_token(user1_id)
        refresh2, _ = jwt_service.create_refresh_token(user2_id)
        
        assert access1 != access2
        assert refresh1 != refresh2

    def test_token_with_account_id(self, jwt_service):
        """Test token creation with account ID."""
        user_id = uuid4()
        account_id = 123456789
        
        access_token = jwt_service.create_access_token(user_id, "free", account_id)
        payload = jwt_service.verify_token(access_token, expected_type="access")
        
        assert payload.sub == str(user_id)
        assert payload.aid == account_id
        assert payload.type == "access"
        assert payload.plan == "free"

    def test_refresh_token_with_custom_jti(self, jwt_service):
        """Test refresh token creation with custom JTI."""
        user_id = uuid4()
        custom_jti = uuid4()
        
        refresh_token, jti = jwt_service.create_refresh_token(user_id, custom_jti)
        payload = jwt_service.verify_token(refresh_token, expected_type="refresh")
        
        assert payload.sub == str(user_id)
        assert payload.jti == str(custom_jti)
        assert jti == custom_jti
        assert payload.type == "refresh"
