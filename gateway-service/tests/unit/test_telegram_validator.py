"""Tests for Telegram validator."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.infrastructure.clients.telegram_validator import TelegramValidator, ParsedTelegramUser


class TestParsedTelegramUser:
    """Tests for ParsedTelegramUser schema."""

    def test_parsed_telegram_user_creation(self):
        """Test ParsedTelegramUser creation."""
        user = ParsedTelegramUser(
            account_id=123456789,
            username="testuser",
            first_name="Test",
            last_name="User",
            language_code="en",
            photo_url="https://t.me/i/userpic/320/testuser.jpg",
            is_premium=True
        )
        
        assert user.account_id == 123456789
        assert user.username == "testuser"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.language_code == "en"
        assert user.photo_url == "https://t.me/i/userpic/320/testuser.jpg"
        assert user.is_premium is True

    def test_parsed_telegram_user_minimal(self):
        """Test ParsedTelegramUser with minimal data."""
        user = ParsedTelegramUser(
            account_id=123456789,
            username=None,
            first_name=None,
            last_name=None,
            language_code=None,
            photo_url=None,
            is_premium=False
        )
        
        assert user.account_id == 123456789
        assert user.username is None
        assert user.first_name is None
        assert user.last_name is None
        assert user.language_code is None
        assert user.photo_url is None
        assert user.is_premium is False


class TestTelegramValidator:
    """Tests for TelegramValidator."""

    @pytest.fixture
    def validator(self):
        """Create TelegramValidator instance."""
        return TelegramValidator(
            bot_token="test_bot_token",
            max_auth_age_seconds=600
        )

    @patch("app.auth.telegram_validator.InitData")
    def test_validate_and_parse_success(self, mock_init_data_class, validator):
        """Test successful validation and parsing."""
        # Mock InitData instance
        mock_init_data = MagicMock()
        mock_init_data.verify.return_value = True
        mock_init_data.auth_date = int(datetime.utcnow().timestamp())
        
        # Mock user data
        mock_user = MagicMock()
        mock_user.id = 123456789
        mock_user.username = "testuser"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.language_code = "en"
        mock_user.is_premium = True
        mock_user.photo_url = "https://t.me/i/userpic/320/testuser.jpg"
        
        mock_init_data.user = mock_user
        mock_init_data_class.parse.return_value = mock_init_data
        
        # Test validation
        result = validator.validate_and_parse("test_init_data")
        
        assert isinstance(result, ParsedTelegramUser)
        assert result.account_id == 123456789
        assert result.username == "testuser"
        assert result.first_name == "Test"
        assert result.last_name == "User"
        assert result.language_code == "en"
        assert result.is_premium is True
        assert result.photo_url == "https://t.me/i/userpic/320/testuser.jpg"

    @patch("app.auth.telegram_validator.InitData")
    def test_validate_and_parse_invalid_signature(self, mock_init_data_class, validator):
        """Test validation with invalid signature."""
        # Mock InitData instance with invalid signature
        mock_init_data = MagicMock()
        mock_init_data.verify.return_value = False
        mock_init_data_class.parse.return_value = mock_init_data
        
        with pytest.raises(ValueError, match="Invalid init_data signature"):
            validator.validate_and_parse("test_init_data")

    @patch("app.auth.telegram_validator.InitData")
    def test_validate_and_parse_no_user_data(self, mock_init_data_class, validator):
        """Test validation with no user data."""
        # Mock InitData instance without user
        mock_init_data = MagicMock()
        mock_init_data.verify.return_value = True
        mock_init_data.user = None
        mock_init_data_class.parse.return_value = mock_init_data
        
        with pytest.raises(ValueError, match="User data not found in init_data"):
            validator.validate_and_parse("test_init_data")

    @patch("app.auth.telegram_validator.InitData")
    def test_validate_and_parse_expired_auth(self, mock_init_data_class, validator):
        """Test validation with expired auth data."""
        # Mock InitData instance with old auth date
        mock_init_data = MagicMock()
        mock_init_data.verify.return_value = True
        mock_init_data.auth_date = int((datetime.utcnow() - timedelta(seconds=700)).timestamp())
        
        mock_user = MagicMock()
        mock_user.id = 123456789
        mock_user.username = "testuser"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.language_code = "en"
        mock_user.is_premium = False
        mock_user.photo_url = None
        
        mock_init_data.user = mock_user
        mock_init_data_class.parse.return_value = mock_init_data
        
        with pytest.raises(ValueError, match="init_data is too old"):
            validator.validate_and_parse("test_init_data")

    @patch("app.auth.telegram_validator.InitData")
    def test_validate_and_parse_parse_error(self, mock_init_data_class, validator):
        """Test validation with parse error."""
        from init_data_py.errors.errors import InitDataPyError
        
        mock_init_data_class.parse.side_effect = InitDataPyError("Invalid format")
        
        with pytest.raises(ValueError, match="Invalid init_data format"):
            validator.validate_and_parse("invalid_init_data")

    @patch("app.auth.telegram_validator.InitData")
    def test_validate_and_parse_general_error(self, mock_init_data_class, validator):
        """Test validation with general error."""
        mock_init_data_class.parse.side_effect = Exception("General error")
        
        with pytest.raises(ValueError, match="Failed to parse init_data"):
            validator.validate_and_parse("test_init_data")

    @patch("app.auth.telegram_validator.InitData")
    def test_validate_and_parse_user_without_optional_fields(self, mock_init_data_class, validator):
        """Test validation with user missing optional fields."""
        # Mock InitData instance
        mock_init_data = MagicMock()
        mock_init_data.verify.return_value = True
        mock_init_data.auth_date = int(datetime.utcnow().timestamp())
        
        # Mock user data without optional fields
        mock_user = MagicMock()
        mock_user.id = 123456789
        # Don't set optional attributes
        del mock_user.username
        del mock_user.first_name
        del mock_user.last_name
        del mock_user.language_code
        del mock_user.is_premium
        del mock_user.photo_url
        
        mock_init_data.user = mock_user
        mock_init_data_class.parse.return_value = mock_init_data
        
        # Test validation
        result = validator.validate_and_parse("test_init_data")
        
        assert isinstance(result, ParsedTelegramUser)
        assert result.account_id == 123456789
        assert result.username is None
        assert result.first_name is None
        assert result.last_name is None
        assert result.language_code is None
        assert result.is_premium is False
        assert result.photo_url is None

    @patch("app.auth.telegram_validator.InitData")
    def test_validate_and_parse_user_with_none_premium(self, mock_init_data_class, validator):
        """Test validation with user having None is_premium."""
        # Mock InitData instance
        mock_init_data = MagicMock()
        mock_init_data.verify.return_value = True
        mock_init_data.auth_date = int(datetime.utcnow().timestamp())
        
        # Mock user data with None is_premium
        mock_user = MagicMock()
        mock_user.id = 123456789
        mock_user.username = "testuser"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.language_code = "en"
        mock_user.is_premium = None
        mock_user.photo_url = None
        
        mock_init_data.user = mock_user
        mock_init_data_class.parse.return_value = mock_init_data
        
        # Test validation
        result = validator.validate_and_parse("test_init_data")
        
        assert isinstance(result, ParsedTelegramUser)
        assert result.account_id == 123456789
        assert result.is_premium is False

    @patch("app.auth.telegram_validator.InitData")
    def test_validate_and_parse_user_with_empty_photo_url(self, mock_init_data_class, validator):
        """Test validation with user having empty photo_url."""
        # Mock InitData instance
        mock_init_data = MagicMock()
        mock_init_data.verify.return_value = True
        mock_init_data.auth_date = int(datetime.utcnow().timestamp())
        
        # Mock user data with empty photo_url
        mock_user = MagicMock()
        mock_user.id = 123456789
        mock_user.username = "testuser"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.language_code = "en"
        mock_user.is_premium = False
        mock_user.photo_url = ""
        
        mock_init_data.user = mock_user
        mock_init_data_class.parse.return_value = mock_init_data
        
        # Test validation
        result = validator.validate_and_parse("test_init_data")
        
        assert isinstance(result, ParsedTelegramUser)
        assert result.account_id == 123456789
        assert result.photo_url is None

    def test_validator_initialization(self):
        """Test TelegramValidator initialization."""
        validator = TelegramValidator(
            bot_token="test_bot_token",
            max_auth_age_seconds=300
        )
        
        assert validator.bot_token == "test_bot_token"
        assert validator.max_auth_age_seconds == 300

    def test_validator_default_max_auth_age(self):
        """Test TelegramValidator with default max_auth_age."""
        validator = TelegramValidator(bot_token="test_bot_token")
        
        assert validator.bot_token == "test_bot_token"
        assert validator.max_auth_age_seconds == 600
