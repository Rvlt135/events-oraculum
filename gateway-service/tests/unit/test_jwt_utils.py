"""Tests for JWT utilities."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from uuid import uuid4, UUID

from app.auth.jwt_utils import JWTService


class TestJWTService:
    """Tests for JWTService."""

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

    def test_create_tokens(self, jwt_service):
        """Test token creation."""
        user_id = uuid4()
        
        access_token = jwt_service.create_access_token(user_id, "free")
        refresh_token, jti = jwt_service.create_refresh_token(user_id)
        
        assert isinstance(access_token, str)
        assert isinstance(refresh_token, str)
        assert isinstance(jti, UUID)
        assert len(access_token) > 0
        assert len(refresh_token) > 0
        assert access_token != refresh_token

    def test_create_tokens_different_users(self, jwt_service):
        """Test token creation for different users."""
        user1_id = uuid4()
        user2_id = uuid4()
        
        access1 = jwt_service.create_access_token(user1_id, "free")
        access2 = jwt_service.create_access_token(user2_id, "free")
        refresh1, _ = jwt_service.create_refresh_token(user1_id)
        refresh2, _ = jwt_service.create_refresh_token(user2_id)
        
        assert access1 != access2
        assert refresh1 != refresh2

    def test_verify_token_access(self, jwt_service):
        """Test access token verification."""
        user_id = uuid4()
        access_token = jwt_service.create_access_token(user_id, "free")
        
        payload = jwt_service.verify_token(access_token, expected_type="access")
        
        assert payload.sub == str(user_id)
        assert payload.type == "access"
        assert payload.plan == "free"
        assert payload.exp > 0
        assert payload.iat > 0

    def test_verify_token_refresh(self, jwt_service):
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

    def test_verify_token_invalid_token(self, jwt_service):
        """Test verification of invalid token."""
        with pytest.raises(ValueError, match="Invalid token"):
            jwt_service.verify_token("invalid_token", expected_type="access")

    def test_verify_token_expired_token(self, jwt_service):
        """Test verification of expired token."""
        # Create a service with very short TTL
        short_jwt_service = JWTService(
            secret="test_secret_key_min_32_chars_long",
            algorithm="HS256",
            access_ttl=1,  # 1 second
            refresh_ttl=1
        )
        
        user_id = uuid4()
        access_token = short_jwt_service.create_access_token(user_id, "free")
        
        # Wait for token to expire
        import time
        time.sleep(2)
        
        with pytest.raises(ValueError, match="Token has expired"):
            short_jwt_service.verify_token(access_token, expected_type="access")

    def test_verify_token_malformed_token(self, jwt_service):
        """Test verification of malformed token."""
        with pytest.raises(ValueError, match="Invalid token"):
            jwt_service.verify_token("not.a.valid.jwt", expected_type="access")

    def test_verify_token_wrong_secret(self, jwt_service):
        """Test verification with wrong secret."""
        # Create another service with different secret
        other_jwt_service = JWTService(
            secret="different_secret_key_min_32_chars_long",
            algorithm="HS256",
            access_ttl=900,
            refresh_ttl=1209600
        )
        
        user_id = uuid4()
        access_token = jwt_service.create_access_token(user_id, "free")
        
        with pytest.raises(ValueError, match="Invalid token"):
            other_jwt_service.verify_token(access_token, expected_type="access")

    def test_token_expiration_times(self, jwt_service):
        """Test that tokens have correct expiration times."""
        user_id = uuid4()
        access_token = jwt_service.create_access_token(user_id, "free")
        refresh_token, _ = jwt_service.create_refresh_token(user_id)
        
        access_payload = jwt_service.verify_token(access_token, expected_type="access")
        refresh_payload = jwt_service.verify_token(refresh_token, expected_type="refresh")
        
        # Check that access token expires before refresh token
        assert access_payload.exp < refresh_payload.exp
        
        # Check that expiration times are reasonable
        now = datetime.utcnow().timestamp()
        access_exp = access_payload.exp
        refresh_exp = refresh_payload.exp
        
        # Access token should expire in about 900 seconds (15 minutes)
        assert 800 <= (access_exp - now) <= 900
        
        # Refresh token should expire in about 1209600 seconds (14 days)
        assert 1200000 <= (refresh_exp - now) <= 1209600

    def test_token_contains_correct_claims(self, jwt_service):
        """Test that tokens contain correct claims."""
        user_id = uuid4()
        access_token = jwt_service.create_access_token(user_id, "free")
        refresh_token, jti = jwt_service.create_refresh_token(user_id)
        
        access_payload = jwt_service.verify_token(access_token, expected_type="access")
        refresh_payload = jwt_service.verify_token(refresh_token, expected_type="refresh")
        
        # Both tokens should have sub, type, exp, iat
        assert access_payload.sub == str(user_id)
        assert access_payload.type == "access"
        assert access_payload.plan == "free"
        assert access_payload.exp > 0
        assert access_payload.iat > 0
        
        assert refresh_payload.sub == str(user_id)
        assert refresh_payload.type == "refresh"
        assert refresh_payload.jti == str(jti)
        assert refresh_payload.exp > 0
        assert refresh_payload.iat > 0

    def test_different_algorithms(self):
        """Test JWT service with different algorithms."""
        # Test with HS256
        hs256_service = JWTService(
            secret="test_secret_key_min_32_chars_long",
            algorithm="HS256",
            access_ttl=900,
            refresh_ttl=1209600
        )
        
        user_id = uuid4()
        access_token = hs256_service.create_access_token(user_id, "free")
        
        payload = hs256_service.verify_token(access_token, expected_type="access")
        assert payload.sub == str(user_id)

    def test_token_serialization(self, jwt_service):
        """Test that tokens can be serialized and deserialized."""
        user_id = uuid4()
        access_token = jwt_service.create_access_token(user_id, "free")
        refresh_token, _ = jwt_service.create_refresh_token(user_id)
        
        # Tokens should be strings
        assert isinstance(access_token, str)
        assert isinstance(refresh_token, str)
        
        # Tokens should contain dots (JWT format)
        assert access_token.count(".") == 2
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

    def test_token_verification_without_type_check(self, jwt_service):
        """Test token verification without type checking."""
        user_id = uuid4()
        access_token = jwt_service.create_access_token(user_id, "free")
        
        # Should work without specifying expected_type
        payload = jwt_service.verify_token(access_token)
        assert payload.sub == str(user_id)
        assert payload.type == "access"
