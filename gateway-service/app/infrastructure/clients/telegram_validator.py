from datetime import UTC, datetime, timedelta

from init_data_py import InitData
from init_data_py.errors.errors import InitDataPyError as InitDataValidationError
from pydantic import BaseModel

from app.config.settings import settings


class ParsedTelegramUser(BaseModel):
    account_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    language_code: str | None
    photo_url: str | None
    is_premium: bool


class TelegramValidator:
    def __init__(self, bot_token: str, max_auth_age_seconds: int = 600):
        self.bot_token = bot_token
        self.max_auth_age_seconds = max_auth_age_seconds

    def validate_and_parse(self, init_data_str: str) -> ParsedTelegramUser:
        try:
            init_data = InitData.parse(init_data_str)
        except InitDataValidationError as e:
            raise ValueError(f"Invalid init_data format: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to parse init_data: {str(e)}")

        if not init_data.verify(self.bot_token):
            raise ValueError("Invalid init_data signature")

        if not init_data.user:
            raise ValueError("User data not found in init_data")

        auth_date = datetime.fromtimestamp(init_data.auth_date)
        age = datetime.now(UTC) - auth_date

        if age > timedelta(seconds=self.max_auth_age_seconds):
            raise ValueError(f"init_data is too old (age: {age.total_seconds()}s)")

        user = init_data.user

        is_premium = False
        if hasattr(user, 'is_premium') and user.is_premium is not None:
            is_premium = bool(user.is_premium)

        photo_url = None
        if hasattr(user, 'photo_url') and user.photo_url:
            photo_url = user.photo_url

        return ParsedTelegramUser(
            account_id=user.id,
            username=user.username if hasattr(user, 'username') else None,
            first_name=user.first_name if hasattr(user, 'first_name') else None,
            last_name=user.last_name if hasattr(user, 'last_name') else None,
            language_code=user.language_code if hasattr(user, 'language_code') else None,
            photo_url=photo_url,
            is_premium=is_premium,
        )

telegram_validator = TelegramValidator(
    bot_token=settings.telegram_bot_token,
    max_auth_age_seconds=settings.telegram_max_auth_age_seconds,
)
