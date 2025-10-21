# Layerbit-Oraculum-AI

AI-система для анализа спортивных событий с прогнозированием исходов через ансамбль LLM-агентов. Полнофункциональная платформа включает сбор odds, AI-анализ, авторизацию и современный веб-интерфейс.

## Архитектура

Микросервисная архитектура с четкой сегрегацией ответственности:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Frontend       │────▶│  Gateway Service │────▶│ Edge Agents     │
│  (React/Vite)   │     │  (Auth + API)    │     │ (AI Analysis)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │                          │
                               ▼                          ▼
                        ┌──────────────┐         ┌──────────────┐
                        │  PostgreSQL  │◀────────│ Odds Service │
                        │  (Primary DB)│         │ (Data Sync)  │
                        └──────────────┘         └──────────────┘
                               ▲
                               │
                        ┌──────────────┐
                        │    Redis     │
                        │ (Cache/Queue)│
                        └──────────────┘
```

## Структура проекта

```
layerbit-oraculum-ai/
├── frontend/
│   └── oraculum-dashboard/       # React + TypeScript + Vite
│       ├── src/
│       │   ├── pages/            # Auth, Dashboard, EventDetail, History, Pricing
│       │   ├── components/       # Reusable UI components
│       │   ├── store/            # Zustand state management
│       │   └── mocks/            # Mock data for demo
│       └── package.json
│
├── gateway-service/              # FastAPI - Public API + Auth
│   ├── app/
│   │   ├── auth/                # JWT, OAuth, password hashing
│   │   │   ├── jwt_utils.py
│   │   │   ├── password_utils.py (argon2)
│   │   │   ├── google_oauth.py
│   │   │   ├── service.py
│   │   │   ├── repositories.py
│   │   │   └── schemas.py
│   │   ├── domain/
│   │   │   └── auth_models.py   # User, UserIdentity, UserSession
│   │   ├── routes/
│   │   │   ├── auth.py          # /auth/* endpoints
│   │   │   ├── insights.py      # /v1/insights/*
│   │   │   └── stats.py         # /v1/stats/*
│   │   ├── services/
│   │   ├── cache/               # Redis caching
│   │   ├── security/            # API key validation
│   │   └── main.py
│   └── requirements.txt
│
├── odds-service/                # FastAPI - Odds collection
│   ├── app/
│   │   ├── adapters/            # The Odds API integration
│   │   ├── tasks/               # TaskIQ workers (collector, normalizer)
│   │   ├── domain/              # Pydantic models
│   │   ├── infra/               # DB + Redis clients
│   │   ├── routes/              # Admin endpoints
│   │   └── main.py
│   ├── boot/
│   │   ├── worker.py            # TaskIQ worker
│   │   └── scheduler.py         # Cron scheduler
│   └── db/schema.sql
│
├── edge-agents-service/         # FastAPI - AI Analysis
│   ├── app/
│   │   ├── services/
│   │   │   ├── agents/          # LLM agent implementations
│   │   │   ├── clients/         # LiteLLM, LangChain, OpenAI
│   │   │   ├── prompts/         # Prompt templates (YAML)
│   │   │   ├── features.py      # Feature engineering
│   │   │   └── runner.py        # Analysis orchestration
│   │   ├── models/              # recommendation.py (SQLAlchemy)
│   │   ├── routes/
│   │   │   ├── internal.py      # /_agents/*
│   │   │   └── run.py           # Batch processing
│   │   └── main.py
│   └── prompts/                 # Agent prompt templates
│
└── infrastructure/
    ├── docker-compose.yml
    ├── docker-compose.infra.yml
    ├── docker-compose.odds.yml
    ├── docker-compose.agents.yml
    └── docker-compose.gateway.yml
```

## Сервисы

### 1. Frontend (oraculum-dashboard)

**Стек:** React 19, TypeScript, Vite, TailwindCSS, Zustand, React Router

**Возможности:**
- Авторизация (mock: login/register forms)
- Тарифные планы (Free/Pro) с ограничениями доступа
- Dashboard с фильтрацией событий по виду спорта, лиге, edge score
- Детальная страница события с:
  - Odds динамикой (Recharts)
  - AI reasoning (summary/full по плану)
  - Контекстом (погода, травмы, форма)
  - AI Voting breakdown (по плану)
- История предсказаний vs фактические результаты
- Plan gating (замочки для locked контента)

**Запуск:**
```bash
cd frontend/oraculum-dashboard
npm install
npm run dev     # http://localhost:5173
npm run build
```

**Планы подписки:**
- **Free/Trial:** 20 событий/день, только футбол, summary reasoning, 3 дня истории
- **Pro:** 100 событий/день, все виды спорта, full analysis, unlimited history

### 2. Gateway Service

**Стек:** FastAPI, SQLAlchemy 2.0 (async), Redis, PyJWT, argon2-cffi, httpx

**Возможности:**

#### Авторизация (NEW)
- **Email/Password:** Registration + Login с argon2 hashing
- **Google OAuth:** Full OAuth 2.0 flow (start → callback)
- **JWT Tokens:** Access (15min) + Refresh (14 days)
- **Session Management:** Redis caching, logout, token refresh
- **User Plans:** free/pro/partner с trial периодом (7 дней)
- **Plan Gating:** Middleware для ограничения доступа по плану

**API Endpoints:**

**Auth:**
- `GET /auth/google/start` - OAuth redirect
- `GET /auth/google/callback` - OAuth callback
- `POST /auth/email/register` - Регистрация
- `POST /auth/email/login` - Вход
- `POST /auth/logout` - Выход
- `POST /auth/token/refresh` - Обновление токена
- `GET /auth/me` - Профиль пользователя

**Insights (requires auth):**
- `GET /v1/insights/recommendations` - Список рекомендаций (paginated)
- `GET /v1/insights/events/{event_id}` - Детали события

**Stats:**
- `GET /v1/stats/summary` - Статистика

**Пример:**
```bash
# Регистрация
curl -X POST http://localhost:8080/auth/email/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepass123"}'

# Получение рекомендаций
curl http://localhost:8080/v1/insights/recommendations \
  -H "Authorization: Bearer <access_token>"
```

**База данных (Auth):**
- `users` - email, password_hash, plan_type, trial_end_at
- `user_identities` - Google/Password identity linking
- `user_sessions` - Refresh token sessions

**Redis Keys:**
- `user:{user_id}` - User profile cache (5min TTL)
- `session:{jti}` - Active refresh sessions
- `blacklist:{jti}` - Invalidated tokens (optional)

### 3. Odds Service

**Стек:** FastAPI, TaskIQ, PostgreSQL, Redis, httpx

**Возможности:**
- Сбор odds из The Odds API
- Нормализация команд и bookmakers
- Агрегация (avg/best odds)
- Автоматический сбор (cron: 9:00, 19:00 UTC)
- Admin API для ручного запуска

**API:**
- `POST /_admin/tasks/collect` - Запуск сбора
- `GET /_admin/data/snapshots` - Просмотр данных
- `GET /health`, `GET /metrics`

**Таблицы:**
- `sports`, `leagues`, `teams`, `events`, `bookmakers`
- `odds_snapshots` - Сырые данные
- `normalized_odds` - Агрегированная статистика

### 4. Edge Agents Service

**Стек:** FastAPI, LiteLLM, LangChain, OpenAI Instructor, PostgreSQL

**Возможности:**
- AI-анализ событий через LLM (OpenRouter)
- Feature engineering (форма команд, H2H, odds движение)
- Генерация рекомендаций (pick, confidence, reasoning)
- Поддержка множественных агентов (betting, conservative, value-hunting)
- Extensible архитектура для voting

**API:**
- `POST /_agents/run_batch` - Запуск анализа
- `GET /_agents/recommendations` - Получение рекомендаций
- `GET /health`

**Prompts:** YAML-шаблоны в `/prompts/`

**Таблица:**
- `recommendations` - AI predictions (pick, confidence, explanation, reasoning)

## Быстрый старт

### Полная инфраструктура

```bash
# 1. Настроить переменные окружения
cp odds-service/.env.example odds-service/.env
cp edge-agents-service/.env.example edge-agents-service/.env
cp gateway-service/.env.example gateway-service/.env

# Отредактировать .env файлы:
# - ODDS_API_KEY (The Odds API)
# - OPENROUTER_API_KEY (OpenRouter)
# - JWT_SECRET (Gateway)
# - GOOGLE_CLIENT_ID/SECRET (опционально)

# 2. Запустить инфраструктуру
cd infrastructure
docker-compose -f docker-compose.infra.yml up -d  # PostgreSQL + Redis

# 3. Запустить сервисы
docker-compose -f docker-compose.odds.yml up -d    # Odds collection
docker-compose -f docker-compose.agents.yml up -d  # AI agents
docker-compose -f docker-compose.gateway.yml up -d # Gateway + Auth

# Или все сразу:
docker-compose up -d
```

### Локальная разработка

**Frontend:**
```bash
cd frontend/oraculum-dashboard
npm install
npm run dev  # http://localhost:5173
```

**Gateway:**
```bash
cd gateway-service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

**Odds:**
```bash
cd odds-service
pip install -r requirements.txt

# Worker
python boot/worker.py

# Admin API
python boot/admin_api.py
```

**Edge Agents:**
```bash
cd edge-agents-service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8082
```

## Endpoints Summary

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:5173 | Web UI |
| Gateway | http://localhost:8080 | Public API + Auth |
| Odds Admin | http://localhost:8081 | Internal admin |
| Edge Agents | http://localhost:8082 | Internal AI API |
| PostgreSQL | localhost:5432 | Database |
| Redis | localhost:6379 | Cache + Queue |

## Environment Variables

**Gateway Service:**
```bash
JWT_SECRET=your_secret_min_32_chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_TTL_SECONDS=900
REFRESH_TOKEN_TTL_SECONDS=1209600
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8080/auth/google/callback
PASSWORD_HASH_SCHEME=argon2
```

**Odds Service:**
```bash
ODDS_API_KEY=your_api_key_from_the_odds_api
```

**Edge Agents:**
```bash
OPENROUTER_API_KEY=your_openrouter_api_key
LLM_PROVIDER=litellm  # или langchain, openai
```

## Технологический стек

**Backend:**
- Python 3.12+
- FastAPI (async)
- SQLAlchemy 2.0 (async)
- TaskIQ (task queue)
- Redis 7
- PostgreSQL 15
- PyJWT, argon2-cffi
- httpx, Pydantic v2
- structlog

**Frontend:**
- React 19
- TypeScript
- Vite
- TailwindCSS
- Zustand
- React Router v7
- Recharts
- Lucide Icons

**AI/LLM:**
- LiteLLM
- LangChain
- OpenAI Instructor
- OpenRouter API

## Принципы разработки

- **Services-First:** Каждый сервис полностью независим
- **No Shared Code:** Готовность к экстракции в отдельные репозитории
- **Database-Driven:** Взаимодействие через PostgreSQL
- **Clean Architecture:** Слои domain, infra, adapters, routes
- **Async-First:** Все I/O операции асинхронные
- **Type Safety:** Pydantic v2 для валидации, TypeScript для frontend
- **Observability:** Prometheus metrics, structlog JSON logging

## Build & Test

```bash
# Build all Python services
npm run build

# Run infrastructure
npm run infra:up

# Run specific service
npm run odds:up
npm run agents:up
npm run gateway:up

# View logs
npm run gateway:logs
```

## License

Proprietary - Layerbit
