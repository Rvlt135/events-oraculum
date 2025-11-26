# TelegramInfo Schema Documentation

## Обзор

`TelegramInfo` - это Pydantic схема для хранения информации о пользователе Telegram в системе аутентификации Gateway Service.

## Структура схемы

```python
class TelegramInfo(BaseModel):
    """Schema for Telegram user information."""
    account_id: int = Field(..., description="Telegram account ID")
    username: str | None = Field(None, description="Telegram username")
    first_name: str | None = Field(None, description="First name from Telegram")
    last_name: str | None = Field(None, description="Last name from Telegram")
    language_code: str | None = Field(None, description="Language code from Telegram")
    photo_url: str | None = Field(None, description="Profile photo URL from Telegram")
    is_premium: bool = Field(False, description="Whether user has Telegram Premium")
```

## Поля

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| `account_id` | `int` | ✅ | Уникальный идентификатор аккаунта Telegram |
| `username` | `str \| None` | ❌ | Имя пользователя в Telegram (без @) |
| `first_name` | `str \| None` | ❌ | Имя пользователя |
| `last_name` | `str \| None` | ❌ | Фамилия пользователя |
| `language_code` | `str \| None` | ❌ | Код языка пользователя (например, "en", "ru") |
| `photo_url` | `str \| None` | ❌ | URL аватара пользователя |
| `is_premium` | `bool` | ❌ | Статус Telegram Premium (по умолчанию: `False`) |

## Использование

### Создание экземпляра

```python
from app.auth.schemas import TelegramInfo

# Минимальный экземпляр
telegram_info = TelegramInfo(account_id=123456789)

# Полный экземпляр
telegram_info = TelegramInfo(
    account_id=123456789,
    username="johndoe",
    first_name="John",
    last_name="Doe",
    language_code="en",
    photo_url="https://t.me/i/userpic/320/johndoe.jpg",
    is_premium=True
)
```

### В составе UserProfile

```python
from app.auth.schemas import UserProfile, TelegramInfo

user_profile = UserProfile(
    id=user_id,
    email="user@example.com",
    email_verified=True,
    plan_type="free",
    trial_end_at=None,
    created_at=datetime.utcnow(),
    telegram=TelegramInfo(
        account_id=123456789,
        username="johndoe",
        first_name="John",
        last_name="Doe"
    )
)
```

## Интеграция с API

### Эндпоинт `/auth/me`

Возвращает профиль пользователя с информацией о Telegram:

```json
{
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "email_verified": true,
    "plan_type": "free",
    "trial_end_at": null,
    "created_at": "2024-01-01T00:00:00Z",
    "telegram": {
      "account_id": 123456789,
      "username": "johndoe",
      "first_name": "John",
      "last_name": "Doe",
      "language_code": "en",
      "photo_url": "https://t.me/i/userpic/320/johndoe.jpg",
      "is_premium": true
    }
  },
  "trial_left_days": null,
  "is_trial_active": false
}
```

### Эндпоинт `/auth/telegram`

При успешной аутентификации через Telegram возвращает:

```json
{
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": null,
    "email_verified": false,
    "plan_type": "free",
    "trial_end_at": null,
    "created_at": "2024-01-01T00:00:00Z",
    "telegram": {
      "account_id": 123456789,
      "username": "johndoe",
      "first_name": "John",
      "last_name": "Doe",
      "language_code": "en",
      "photo_url": "https://t.me/i/userpic/320/johndoe.jpg",
      "is_premium": true
    }
  },
  "tokens": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer"
  }
}
```

## Валидация

Схема автоматически валидирует:

- `account_id` должен быть положительным целым числом
- `username` должен быть строкой или `null`
- `first_name` должен быть строкой или `null`
- `last_name` должен быть строкой или `null`
- `language_code` должен быть строкой или `null`
- `photo_url` должен быть валидным URL или `null`
- `is_premium` должен быть булевым значением

## Примеры использования в коде

### В маршрутах аутентификации

```python
# app/routes/auth.py
telegram_info = TelegramInfo(
    account_id=user.telegram_account_id,
    username=telegram_identity.username,
    first_name=telegram_identity.first_name,
    last_name=telegram_identity.last_name,
    language_code=telegram_identity.language_code,
    photo_url=telegram_identity.photo_url,
    is_premium=telegram_identity.is_premium or False,
)

user_profile = UserProfile.model_validate(user)
user_profile.telegram = telegram_info
```

### В тестах

```python
def test_telegram_info_creation():
    telegram_info = TelegramInfo(
        account_id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User",
        is_premium=True
    )
    
    assert telegram_info.account_id == 123456789
    assert telegram_info.username == "testuser"
    assert telegram_info.is_premium is True
    assert telegram_info.photo_url is None
```

## OpenAPI документация

Схема автоматически генерируется в OpenAPI спецификации и доступна в Swagger UI по адресу `/docs`.

## Связанные компоненты

- `UserProfile` - основная схема профиля пользователя
- `ParsedTelegramUser` - схема для парсинга данных от Telegram WebApp
- `TelegramValidator` - валидатор данных Telegram
- `UserIdentity` - модель базы данных для хранения идентификаторов
