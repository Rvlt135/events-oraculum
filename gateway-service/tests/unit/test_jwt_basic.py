"""Basic tests for JWT utilities - only creation, no verification."""

import pytest
from uuid import uuid4, UUID

from app.infrastructure.security.jwt import JWTService


class TestJWTServiceBasic:
    """Basic tests for JWTService - only creation."""

    @pytest.fixture
    def jwt_service(self):
        """Create JWTService instance."""
        return JWTService(
            secret="test_secret_key_min_32_chars_long",
            algorithm="HS256",
            access_ttl=900,
            refresh_ttl=1209600
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
        assert refresh_token.count(".") == 2

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
        
        assert isinstance(access_token, str)
        assert len(access_token) > 0
        assert access_token.count(".") == 2  # JWT format

    def test_refresh_token_with_custom_jti(self, jwt_service):
        """Test refresh token creation with custom JTI."""
        user_id = uuid4()
        custom_jti = uuid4()
        
        refresh_token, jti = jwt_service.create_refresh_token(user_id, custom_jti)
        
        assert isinstance(refresh_token, str)
        assert jti == custom_jti
        assert len(refresh_token) > 0
        assert refresh_token.count(".") == 2  # JWT format

    def test_different_plan_types(self, jwt_service):
        """Test token creation with different plan types."""
        user_id = uuid4()
        
        free_token = jwt_service.create_access_token(user_id, "free")
        pro_token = jwt_service.create_access_token(user_id, "pro")
        partner_token = jwt_service.create_access_token(user_id, "partner")
        
        assert isinstance(free_token, str)
        assert isinstance(pro_token, str)
        assert isinstance(partner_token, str)
        
        # All should be different
        assert free_token != pro_token
        assert pro_token != partner_token
        assert free_token != partner_token

    def test_token_structure(self, jwt_service):
        """Test that tokens have correct JWT structure."""
        user_id = uuid4()
        access_token = jwt_service.create_access_token(user_id, "free")
        refresh_token, _ = jwt_service.create_refresh_token(user_id)
        
        # JWT tokens should have 3 parts separated by dots
        assert access_token.count(".") == 2
        assert refresh_token.count(".") == 2
        
        # Each part should be non-empty
        access_parts = access_token.split(".")
        refresh_parts = refresh_token.split(".")
        
        assert len(access_parts) == 3
        assert len(refresh_parts) == 3
        
        for part in access_parts + refresh_parts:
            assert len(part) > 0
