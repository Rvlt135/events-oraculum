# Gateway Service

Публичный API сервис для получения инсайтов и рекомендаций по ставкам на спорт. Сервис предоставляет REST API для аутентификации пользователей, получения рекомендаций по ставкам и статистики.

## 🚀 Возможности

- **Аутентификация пользователей** через email/пароль, Google OAuth и Telegram
- **API для получения рекомендаций** по ставкам с фильтрацией по лигам, датам и уверенности
- **Статистика** по рекомендациям и событиям
- **Кэширование** с использованием Redis
- **Мониторинг** с помощью Prometheus метрик
- **Логирование** структурированными логами
- **Миграции базы данных** с помощью Alembic

## 🏗️ Архитектура

Сервис построен на FastAPI с использованием:
- **PostgreSQL** - основная база данных
- **Redis** - кэширование и сессии
- **SQLAlchemy** - ORM для работы с базой данных
- **Alembic** - миграции базы данных
- **Pydantic** - валидация данных
- **Structlog** - структурированное логирование

### 📚 Документация по архитектуре

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Обзор архитектуры и принципов
- **[CLEAN_CODE_ANALYSIS.md](./CLEAN_CODE_ANALYSIS.md)** - Детальный анализ структуры и рекомендации по Clean Code
- **[AUTH_IMPLEMENTATION.md](./AUTH_IMPLEMENTATION.md)** - Документация по реализации аутентификации
- **[API_EXAMPLES.md](./API_EXAMPLES.md)** - Примеры использования API

## 📋 Требования

- Python 3.12+
- PostgreSQL 12+
- Redis 6+
- Docker (опционально)

## 🛠️ Установка и настройка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd gateway-service
```

### 2. Создание виртуального окружения

```bash
python -m venv venv-gateway
source venv-gateway/bin/activate  # Linux/macOS
# или
venv-gateway\Scripts\activate     # Windows
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Настройка базы данных

#### PostgreSQL

```bash
# Создание базы данных
createdb layerbit

# Применение миграций
alembic upgrade head
```

#### Redis

```bash
# Запуск Redis (Docker)
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Или установка локально
# Ubuntu/Debian: sudo apt install redis-server
# macOS: brew install redis
```

### 5. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
# Основные настройки
SERVICE_NAME=gateway-service
ENVIRONMENT=development
LOG_LEVEL=INFO

# API настройки
API_HOST=0.0.0.0
API_PORT=8080
API_KEY=your_secret_api_key_here

# База данных PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=layerbit

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT настройки
JWT_SECRET=your_jwt_secret_min_32_chars_long
JWT_ALGORITHM=HS256
ACCESS_TOKEN_TTL_SECONDS=900
REFRESH_TOKEN_TTL_SECONDS=1209600

# Google OAuth (опционально)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8080/auth/google/callback

# Telegram Bot (опционально)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_MAX_AUTH_AGE_SECONDS=600

# CORS настройки
CORS_ORIGINS=["http://localhost:3000", "https://yourdomain.com"]

# Кэширование
CACHE_TTL_SECONDS=300

# Пагинация
DEFAULT_PAGE_LIMIT=50
MAX_PAGE_LIMIT=500
```

## 🚀 Запуск сервиса

### Локальный запуск

```bash
# Активация виртуального окружения
source venv-gateway/bin/activate

# Запуск сервиса
python -m app.main
```

### Запуск с uvicorn

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### Docker

```bash
# Сборка образа
docker build -t gateway-service .

# Запуск контейнера
docker run -p 8080:8080 --env-file .env gateway-service
```

### Docker Compose

Создайте файл `docker-compose.yml`:

```yaml
version: '3.8'
services:
  gateway-service:
    build: .
    ports:
      - "8080:8080"
    environment:
      - POSTGRES_HOST=postgres
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    env_file:
      - .env

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: layerbit
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

Запуск:

```bash
docker-compose up -d
```

## 📚 API Документация

После запуска сервиса документация доступна по адресам:

- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc
- **OpenAPI JSON**: http://localhost:8080/openapi.json

### Основные эндпоинты

#### Аутентификация (`/auth`)

- `POST /auth/register` - Регистрация с email/паролем
- `POST /auth/login` - Вход с email/паролем
- `POST /auth/telegram` - Аутентификация через Telegram
- `GET /auth/google` - Начало OAuth с Google
- `GET /auth/google/callback` - Callback для Google OAuth
- `POST /auth/refresh` - Обновление токенов
- `POST /auth/logout` - Выход из системы
- `GET /auth/me` - Получение профиля пользователя

#### Инсайты (`/v1/insights`)

- `GET /v1/insights/recommendations` - Получение рекомендаций по ставкам
- `GET /v1/insights/events/{event_id}` - Детали события

#### Статистика (`/v1/stats`)

- `GET /v1/stats/summary` - Сводная статистика

#### Системные

- `GET /` - Информация о сервисе
- `GET /health` - Проверка здоровья
- `GET /metrics` - Prometheus метрики

## 🔧 Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `SERVICE_NAME` | Название сервиса | `gateway-service` |
| `ENVIRONMENT` | Окружение (development/production) | `production` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |
| `API_HOST` | Хост для API | `0.0.0.0` |
| `API_PORT` | Порт для API | `8080` |
| `API_KEY` | Секретный ключ API | `changeme_secret_key` |
| `POSTGRES_HOST` | Хост PostgreSQL | `localhost` |
| `POSTGRES_PORT` | Порт PostgreSQL | `5432` |
| `POSTGRES_USER` | Пользователь PostgreSQL | `postgres` |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL | `postgres` |
| `POSTGRES_DB` | База данных PostgreSQL | `layerbit` |
| `REDIS_URL` | URL Redis | `redis://localhost:6379/0` |
| `JWT_SECRET` | Секрет для JWT | `changeme_jwt_secret_min_32_chars` |
| `JWT_ALGORITHM` | Алгоритм JWT | `HS256` |
| `ACCESS_TOKEN_TTL_SECONDS` | TTL access токена | `900` |
| `REFRESH_TOKEN_TTL_SECONDS` | TTL refresh токена | `1209600` |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID | `` |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret | `` |
| `GOOGLE_REDIRECT_URI` | Google OAuth Redirect URI | `http://localhost:8080/auth/google/callback` |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | `` |
| `TELEGRAM_MAX_AUTH_AGE_SECONDS` | Максимальный возраст Telegram auth | `600` |
| `CORS_ORIGINS` | Разрешенные CORS origins | `["*"]` |
| `CACHE_TTL_SECONDS` | TTL кэша | `300` |
| `DEFAULT_PAGE_LIMIT` | Лимит страниц по умолчанию | `50` |
| `MAX_PAGE_LIMIT` | Максимальный лимит страниц | `500` |

## 🗄️ База данных

### Миграции

Сервис использует Alembic для управления миграциями базы данных.

```bash
# Просмотр текущего состояния
alembic current

# Применение миграций
alembic upgrade head

# Создание новой миграции
alembic revision --autogenerate -m "Описание изменений"

# Откат миграций
alembic downgrade -1
```

Подробная документация по Alembic: [ALEMBIC_README.md](ALEMBIC_README.md)

### Модели данных

- **users** - Пользователи системы
- **user_identities** - Идентификаторы пользователей (OAuth, Telegram)
- **user_sessions** - Сессии пользователей

## 📊 Мониторинг

### Логирование

Сервис использует структурированное логирование с помощью `structlog`. Логи включают:

- Время выполнения запросов
- Информацию о пользователях
- Ошибки и исключения
- Метрики производительности

### Prometheus метрики

Метрики доступны по адресу `/metrics`:

- HTTP запросы и их статусы
- Время выполнения запросов
- Количество активных соединений
- Использование памяти

### Health Check

Эндпоинт `/health` возвращает статус сервиса:

```json
{
  "status": "healthy"
}
```

## 🔒 Безопасность

- **JWT токены** для аутентификации
- **API ключи** для доступа к эндпоинтам
- **CORS** настройки для защиты от CSRF
- **Валидация входных данных** с помощью Pydantic
- **Хэширование паролей** с помощью Argon2

## 🧪 Тестирование

```bash
# Запуск тестов (если есть)
pytest

# Запуск с покрытием
pytest --cov=app
```

## 📦 Развертывание

### Production

1. Установите переменные окружения для production
2. Настройте reverse proxy (nginx)
3. Используйте process manager (systemd, supervisor)
4. Настройте мониторинг и логирование

### Docker

```bash
# Сборка production образа
docker build -t gateway-service:latest .

# Запуск с production настройками
docker run -d \
  --name gateway-service \
  -p 8080:8080 \
  --env-file .env.production \
  gateway-service:latest
```

## 🤝 Разработка

### Структура проекта

```
gateway-service/
└── app/
    ├── api/                                # Presentation: FastAPI
    │   ├── routes/
    │   │   ├── auth.py                     # /auth/*
    │   │   ├── insights.py                 # /v1/insights/*
    │   │   └── stats.py                    # /v1/stats/*
    │   ├── schemas/                        # Pydantic DTO для HTTP (request/response)
    │   │   ├── auth.py
    │   │   ├── user.py
    │   │   └── common.py
    │   └── di/                        # Pydantic DTO для HTTP (request/response)
    │       ├── deps.py                         # FastAPI Depends-фабрики (создание сервисов/репо)
    │       ├── auth_deps.py
    │
    ├── domain/                             # Core: чистые типы и правила (без SQLAlchemy/HTTP)
    │   ├── entities/
    │   │   ├── user.py                     # чистая сущность User (id, plan, email, ...)
    │   │   ├── user_identity.py            # тип/данные учётки (EMAIL/GOOGLE/TELEGRAM)
    │   │   └── user_session.py             # минимальная модель сессии (если нужна в логике)
    │   └── rules/
    │       ├── subscription_rules.py       # can_access_category(plan, category) и пр.
    │       └── auth_rules.py               # базовые бизнес-валидации (без I/O)
    │
    ├── services/                           # Application: оркестрация use-cases
    │   ├── auth_service.py                 # signup/login, Google OAuth, Telegram init_data
    │   ├── insights_service.py
    │   └── stats_service.py
    │
    ├── infrastructure/                     # Интеграции/Хранилище/Безопасность
    │   ├── db/
    │   │   ├── engine.py                   # create_async_engine(...)
    │   │   ├── session.py                  # async_sessionmaker, get_session()
    │   │   ├── orm/                        # ✨ СЮДА ПЕРЕНОСИМ все SQLAlchemy-модели
    │   │   │   ├── user.py                 # UserORM
    │   │   │   ├── user_identity.py        # UserIdentityORM
    │   │   │   └── user_session.py         # UserSessionORM
    │   │   └── repositories/               # тонкие репозитории поверх AsyncSession
    │   │       ├── user_repo.py
    │   │       └── session_repo.py
    │   ├── cache/
    │   │   └── redis.py                    # Redis-клиент/ключи
    │   ├── clients/                        # внешние клиенты/адаптеры
    │   │   ├── google_oauth.py             # Google OAuth (HTTP)
    │   │   └── telegram_validator.py       # Telegram init_data verify (HTTP/crypto)
    │   └── security/
    │       ├── password.py                 # argon2/крипта паролей
    │       └── jwt.py                      # выдача/парсинг JWT
    │
    ├── config/
    │   ├── settings.py                     # Pydantic Settings (.env)
    │   └── policy.py                       # (опц.) централизованные политики/константы
    │
    ├── utils/
    │   └── logging.py                      # structlog конфиг
    │
    ├── app.py                              # FastAPI app + lifespan (инициализация DI)
    └── main.py                             # uvicorn entrypoint

```

### Добавление новых эндпоинтов

1. Создайте роутер в `app/routes/`
2. Добавьте схемы в `app/models/schemas.py`
3. Реализуйте бизнес-логику в `app/services/`
4. Подключите роутер в `app/main.py`

## 📞 Поддержка

Для вопросов и поддержки обращайтесь к команде разработки.

## 📄 Лицензия

[Укажите лицензию проекта]
