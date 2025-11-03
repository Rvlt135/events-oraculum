# Layerbit-Oraculum-AI

AI-система для анализа спортивных событий с прогнозированием исходов через ансамбль LLM-агентов. Полнофункциональная платформа включает сбор odds, AI-анализ, авторизацию и современный веб-интерфейс.

## Архитектура

Микросервисная архитектура с четкой сегрегацией ответственности:

**Поток данных:**
1. **Odds Service** (TaskIQ) собирает данные из внешнего API и записывает в PostgreSQL и Redis кэш
2. **Edge Agents Service** читает готовые данные из БД и кэша, анализирует их через LLM и создает рекомендации
3. **Gateway Service** предоставляет авторизованный API доступ к рекомендациям для Frontend

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Frontend       │────▶│  Gateway Service │────▶│ Edge Agents     │
│  (React/Vite)   │     │  (Auth + API)    │     │ (AI Analysis)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │                          │
                               │                          │
                               ▼                          ▼
                        ┌──────────────┐         ┌──────────────┐
                        │  PostgreSQL  │◀────────│    Redis     │
                        │  (Primary DB)│         │ (Cache/Queue)│
                        └──────────────┘         └──────────────┘
                               ▲                          │
                               │                          │
                        ┌──────────────┐                 │
                        │ Odds Service │─────────────────┘
                        │ (Data Sync)  │  Записывает в кэш и БД
                        │  TaskIQ      │  через TaskIQ worker
                        └──────────────┘
```

## Структура проекта

```
layerbit-oraculs-bet/
│
├── frontend/                                    # Frontend приложение
│   └── oraculum-dashboard/
│       ├── src/
│       │   ├── pages/                           # Страницы приложения
│       │   │   ├── Auth.tsx                    # Авторизация
│       │   │   ├── Dashboard.tsx               # Главная панель
│       │   │   ├── EventDetail.tsx             # Детали события
│       │   │   ├── History.tsx                 # История предсказаний
│       │   │   └── Pricing.tsx                 # Тарифные планы
│       │   ├── components/                     # Переиспользуемые компоненты
│       │   │   ├── EventCard.tsx
│       │   │   ├── FilterBar.tsx
│       │   │   ├── PlanGate.tsx
│       │   │   ├── OddsChart.tsx
│       │   │   └── ...
│       │   ├── store/                          # Zustand state management
│       │   │   └── authStore.ts
│       │   ├── services/                       # API клиенты
│       │   │   └── authService.ts
│       │   └── mocks/                          # Mock данные для разработки
│       ├── package.json
│       └── vite.config.ts
│
├── gateway-service/                             # Gateway Service - Public API + Auth
│   ├── app/
│   │   ├── auth/                               # Модуль авторизации
│   │   │   ├── jwt_utils.py                   # JWT токены
│   │   │   ├── password_utils.py              # Хеширование паролей (argon2)
│   │   │   ├── google_oauth.py                # Google OAuth интеграция
│   │   │   ├── telegram_validator.py          # Telegram валидация
│   │   │   ├── service.py                     # Бизнес-логика auth
│   │   │   ├── repositories.py                # Репозитории БД
│   │   │   ├── schemas.py                     # Pydantic схемы
│   │   │   └── dependencies.py               # FastAPI dependencies
│   │   ├── domain/
│   │   │   └── auth_models.py                  # SQLAlchemy модели (User, UserIdentity, UserSession)
│   │   ├── routes/
│   │   │   ├── auth.py                        # /auth/* endpoints
│   │   │   ├── insights.py                    # /v1/insights/* endpoints
│   │   │   └── stats.py                       # /v1/stats/* endpoints
│   │   ├── services/
│   │   │   ├── insights_service.py
│   │   │   └── stats_service.py
│   │   ├── cache/
│   │   │   └── redis.py                       # Redis клиент для кеширования
│   │   ├── security/
│   │   │   ├── apikey.py                      # API key валидация
│   │   │   └── authorization.py               # Авторизация по планам
│   │   ├── config/
│   │   │   ├── settings.py                    # Pydantic Settings
│   │   │   └── dependencies.py               # Общие dependencies
│   │   ├── db/
│   │   │   ├── pg.py                          # PostgreSQL подключение
│   │   │   └── repositories.py               # Репозитории БД
│   │   ├── observability/
│   │   │   └── logging.py                     # Structlog конфигурация
│   │   └── main.py                            # FastAPI приложение
│   ├── alembic/                                # Миграции БД
│   │   ├── versions/                          # Файлы миграций
│   │   └── env.py
│   ├── tests/                                  # Тесты
│   ├── requirements.txt
│   └── Dockerfile
│
├── odds-service/                                # Odds Service - Сбор котировок
│   ├── app/
│   │   ├── config/                            # Конфигурация
│   │   │   ├── settings.py                    # Настройки приложения
│   │   │   ├── dependencies.py               # DI провайдеры
│   │   │   ├── security.py                   # Безопасность (admin токены)
│   │   │   └── metrics.py                     # Prometheus метрики
│   │   ├── domain/                            # Domain слой
│   │   │   ├── models.py                      # Pydantic модели
│   │   │   ├── orm_models.py                  # SQLAlchemy ORM модели
│   │   │   ├── services/                      # Domain сервисы
│   │   │   ├── ports/                         # Интерфейсы (порты)
│   │   │   └── utils/                         # Утилиты
│   │   ├── infra/                             # Infrastructure слой
│   │   │   ├── repositories/                  # Репозитории БД
│   │   │   │   ├── sport.py
│   │   │   │   ├── competitions.py
│   │   │   │   ├── event.py
│   │   │   │   ├── team.py
│   │   │   │   ├── bookmaker.py
│   │   │   │   ├── odds_snapshot.py
│   │   │   │   └── normalized_odds.py
│   │   │   ├── http/                          # HTTP клиенты
│   │   │   │   └── odds_api.py                # The Odds API клиент
│   │   │   ├── db/                            # База данных
│   │   │   │   ├── orm/                       # ORM модели
│   │   │   │   └── session.py                 # Сессии БД
│   │   │   ├── redis_client.py                # Redis клиент
│   │   │   ├── unit_of_work.py                # Unit of Work паттерн
│   │   │   └── providers.py                  # Infrastructure providers
│   │   ├── tasks/                             # TaskIQ задачи
│   │   │   ├── collector.py                  # Сбор данных из API
│   │   │   ├── normalizer.py                 # Нормализация данных
│   │   │   └── broker.py                     # TaskIQ broker конфигурация
│   │   ├── routes/                            # API маршруты
│   │   │   ├── admin.py                      # /_admin/* endpoints
│   │   │   └── public.py                     # Публичные endpoints
│   │   ├── schemas/                           # Pydantic схемы для API
│   │   └── main.py                            # FastAPI приложение
│   ├── boot/                                   # Запуск сервисов
│   │   ├── worker.py                          # TaskIQ worker
│   │   └── scheduler.py                       # Cron scheduler
│   ├── alembic/                                # Миграции БД
│   │   ├── versions/
│   │   │   └── 55aabbccddee_initial_migration_create_all_tables.py
│   │   └── env.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── edge-agents-service/                        # Edge Agents Service - AI анализ
│   ├── app/
│   │   ├── services/
│   │   │   ├── agents/                        # LLM агенты
│   │   │   │   ├── betting_agent.py
│   │   │   │   ├── conservative_agent.py
│   │   │   │   ├── value_hunting_agent.py
│   │   │   │   └── persistence.py
│   │   │   ├── clients/                       # LLM клиенты
│   │   │   │   ├── litellm_client.py
│   │   │   │   ├── langchain_client.py
│   │   │   │   ├── openai_client.py
│   │   │   │   └── ...
│   │   │   ├── prompts/                       # Шаблоны промптов
│   │   │   │   ├── betting_analysis.py
│   │   │   │   ├── conservative_analysis.py
│   │   │   │   └── value_hunting.py
│   │   │   ├── features.py                    # Feature engineering
│   │   │   └── runner.py                      # Оркестрация анализа
│   │   ├── models/
│   │   │   └── recommendation.py             # SQLAlchemy модель рекомендаций
│   │   ├── routes/
│   │   │   ├── internal.py                    # /_agents/* endpoints
│   │   │   ├── recommendations.py             # Получение рекомендаций
│   │   │   └── run.py                         # Batch обработка
│   │   ├── config/
│   │   │   ├── settings.py
│   │   │   ├── model_loader.py                # Загрузка моделей из YAML
│   │   │   └── models.yaml                    # Конфигурация моделей
│   │   ├── db/
│   │   │   ├── pg.py
│   │   │   └── repositories.py
│   │   ├── cache/
│   │   │   └── redis.py
│   │   ├── tasks/
│   │   │   ├── broker.py
│   │   │   └── run_batch.py
│   │   └── main.py
│   ├── boot/
│   │   ├── worker.py
│   │   └── scheduler.py
│   ├── prompts/                                # YAML шаблоны промптов
│   │   ├── betting_analysis.yml
│   │   ├── conservative_analysis.yml
│   │   └── value_hunting.yml
│   ├── requirements.txt
│   └── Dockerfile
│
└── infrastructure/                              # Docker Compose конфигурации
    ├── docker-compose.yml                      # Все сервисы вместе
    ├── docker-compose.infra.yml                # Инфраструктура (PostgreSQL, Redis)
    ├── docker-compose.odds.yml                 # Odds Service (API, Worker, Scheduler)
    ├── docker-compose.agents.yml               # Edge Agents Service
    └── docker-compose.gateway.yml              # Gateway Service
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

**Стек:** FastAPI, TaskIQ, PostgreSQL, Redis, httpx, Alembic, SQLAlchemy 2.0

**Архитектура:**
- **Clean Architecture:** Разделение на слои domain, infra, routes
- **Dependency Injection:** Через FastAPI dependencies и providers
- **Unit of Work:** Паттерн для управления транзакциями
- **Ports & Adapters:** Интерфейсы для внешних зависимостей

**Возможности:**
- Сбор odds из The Odds API (автоматический по расписанию через TaskIQ)
- Синхронизация sports и competitions из внешнего API
- Нормализация команд и bookmakers
- Агрегация odds (avg/best по всем букмекерам)
- Запись данных в PostgreSQL (нормализованные odds, события, команды)
- Запись в Redis кэш (спортивные каталоги, агрегированные данные)
- Автоматический сбор (cron: 9:00, 19:00 UTC через TaskIQ scheduler)
- TaskIQ worker для обработки задач сбора и нормализации
- Admin API для ручного запуска задач

**TaskIQ:**
- **Broker:** Redis-based broker для очереди задач
- **Worker:** Асинхронный worker для обработки задач сбора и нормализации
- **Scheduler:** Cron scheduler для автоматического запуска задач по расписанию
- **Tasks:**
  - `collect_odds_task` - сбор данных из внешнего API
  - `collect_sports_task` - синхронизация sports и competitions
  - `normalize_odds_task` - нормализация и агрегация odds

**Кэширование в Redis:**
- `catalog:sports` - каталог видов спорта (TTL 10 минут)
- Кэширование нормализованных odds для быстрого доступа
- Очередь задач TaskIQ (Redis List)

**Компоненты:**
- **API Server** (`app/main.py`): FastAPI приложение с admin endpoints
- **Worker** (`boot/worker.py`): TaskIQ worker для обработки задач
- **Scheduler** (`boot/scheduler.py`): Cron scheduler для автоматических задач
- **Tasks** (`app/tasks/`):
  - `collector.py` - сбор данных из внешнего API
  - `normalizer.py` - нормализация и агрегация odds

**API Endpoints:**
- `GET /` - Информация о сервисе
- `GET /health` - Health check
- `GET /readiness` - Readiness probe (Kubernetes)
- `GET /liveness` - Liveness probe (Kubernetes)
- `GET /metrics` - Prometheus метрики
- `POST /_admin/tasks/collect` - Ручной запуск сбора odds (требует admin токен)
- `GET /_admin/data/snapshots` - Просмотр normalized odds (требует admin токен)

**База данных:**
- `sports` - Виды спорта (provider, category, is_active)
- `competitions` - Соревнования/лиги (title, provider_key, sport_id)
- `teams` - Команды с нормализованными именами
- `events` - Спортивные события
- `bookmakers` - Букмекеры
- `odds_snapshots` - Сырые снимки котировок из API
- `normalized_odds` - Агрегированные котировки (avg/best по всем букмекерам)

**Миграции:**
```bash
cd odds-service
alembic upgrade head  # Применить миграции
alembic current       # Проверить текущую версию
```

**Переменные окружения:**
```bash
ODDS_API_KEY=your_api_key
ODDS_API_BASE_URL=https://api.the-odds-api.com/v4
ODDS_API_REGIONS=eu,us
ODDS_API_MARKETS=h2h
ODDS_API_COMPETITIONS=soccer_epl,soccer_uefa_champs_league
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=layerbit
REDIS_URL=redis://localhost:6379/0
ADMIN_ENABLED=true
ADMIN_TOKEN=your_admin_token
```

### 4. Edge Agents Service

**Стек:** FastAPI, LiteLLM, LangChain, OpenAI Instructor, PostgreSQL, Redis, TaskIQ

**Архитектура:**
- **Чтение данных:** Анализирует данные, собранные и обработанные Odds Service
- **Источники данных:** PostgreSQL (нормализованные odds, события) и Redis кэш
- **Feature Engineering:** Извлечение признаков из данных odds для AI анализа
- **LLM Analysis:** Использование множественных LLM агентов для анализа

**Возможности:**
- Чтение данных из PostgreSQL (нормализованные odds, события, команды) - данные, подготовленные Odds Service
- Чтение из Redis кэша (кэшированные агрегированные данные) - данные, записанные Odds Service
- AI-анализ событий через LLM (OpenRouter)
- Feature engineering (форма команд, H2H, динамика odds, статистика)
- Генерация рекомендаций (pick, confidence, reasoning)
- Поддержка множественных агентов (betting, conservative, value-hunting)
- Extensible архитектура для voting ансамбля агентов
- Сохранение рекомендаций в PostgreSQL

**Поток данных:**
1. Odds Service собирает данные через TaskIQ и записывает в PostgreSQL и Redis
2. Edge Agents Service читает готовые данные из БД и кэша
3. Применяет feature engineering и передает в LLM агентов
4. Сохраняет рекомендации в таблицу `recommendations`

**API:**
- `POST /_agents/run_batch` - Запуск анализа батча событий
- `GET /_agents/recommendations` - Получение рекомендаций
- `GET /health`

**Prompts:** YAML-шаблоны в `/prompts/`

**Таблица:**
- `recommendations` - AI predictions (pick, confidence, explanation, reasoning)

**TaskIQ (опционально):**
- Worker для асинхронной обработки анализа
- Scheduler для периодического анализа новых событий

## Быстрый старт

### Предварительные требования

- Docker и Docker Compose
- Python 3.12+ (для локальной разработки)
- Node.js 18+ и npm (для frontend)
- PostgreSQL 15+ (для локальной разработки, или используйте Docker)
- Redis 7+ (для локальной разработки, или используйте Docker)

### Запуск инфраструктуры

**Вариант 1: Docker Compose (рекомендуется)**

```bash
# 1. Клонировать репозиторий
git clone <repository-url>
cd layerbit-oraculs-bet

# 2. Настроить переменные окружения
# Скопировать и заполнить .env файлы для каждого сервиса:
cp gateway-service/env.example gateway-service/.env
cp odds-service/.env.example odds-service/.env  # Если есть
cp edge-agents-service/.env.example edge-agents-service/.env  # Если есть

# Для инфраструктуры можно использовать env.example (если есть):
# cp infrastructure/.env.example infrastructure/.env

# Отредактировать .env файлы:
# - Gateway: JWT_SECRET, GOOGLE_CLIENT_ID/SECRET (опционально)
# - Odds: ODDS_API_KEY
# - Edge Agents: OPENROUTER_API_KEY
# - Infrastructure: настройки PostgreSQL/Redis (опционально)

# 3. Создать Docker network (если еще не создана)
cd infrastructure
docker network create layerbit-net 2>/dev/null || true

# 4. Запустить инфраструктуру (PostgreSQL + Redis)
docker-compose -f docker-compose.infra.yml up -d

# Проверить статус
docker-compose -f docker-compose.infra.yml ps

# Посмотреть логи
docker-compose -f docker-compose.infra.yml logs -f

# 5. Применить миграции баз данных (см. раздел ниже)
```

### Применение миграций баз данных

**Важно:** После запуска инфраструктуры необходимо применить миграции для каждого микросервиса ДО их запуска.

```bash
# Gateway Service миграции
cd gateway-service
source venv-gateway/bin/activate  # или создайте виртуальное окружение
pip install -r requirements.txt
alembic upgrade head
alembic current  # проверить текущую версию миграций

# Odds Service миграции
cd ../odds-service
source venv-odds/bin/activate  # или создайте виртуальное окружение
pip install -r requirements.txt
alembic upgrade head
alembic current  # проверить текущую версию миграций

# Edge Agents Service миграции (если используются)
# cd ../edge-agents-service
# source venv-agents/bin/activate
# pip install -r requirements.txt
# alembic upgrade head  # если используется Alembic

# Альтернативно: применить миграции через Docker (если сервисы уже запущены)
# Gateway Service:
# docker-compose -f ../infrastructure/docker-compose.gateway.yml exec gateway alembic upgrade head
# Odds Service:
# docker-compose -f ../infrastructure/docker-compose.odds.yml exec odds-api alembic upgrade head
```

**Проверка миграций:**
```bash
# Проверить текущую версию миграций
cd gateway-service
alembic current

cd ../odds-service
alembic current

# Посмотреть историю миграций
alembic history

# Откатить миграцию (если нужно)
alembic downgrade -1
```

**Вариант 2: Запуск всех сервисов вместе**

> **Примечание:** Для текущей разработки рекомендуется запускать микросервисы по отдельности (см. раздел "Запуск сервисов по отдельности").

```bash
cd infrastructure

# Создать Docker network (если еще не создана)
docker network create layerbit-net 2>/dev/null || true

# Для инфраструктуры можно использовать env.example (если есть):
# cp .env.example .env

# Запустить все сервисы
docker-compose up -d

# Проверить статус всех сервисов
docker-compose ps

# Посмотреть логи конкретного сервиса
docker-compose logs -f gateway
docker-compose logs -f odds-api
docker-compose logs -f edge-agents
```

### Запуск сервисов по отдельности

> **Рекомендация для разработки:** Запускайте микросервисы по отдельности для удобства разработки, отладки и логирования. Это позволяет:
> - Легче отслеживать логи конкретного сервиса
> - Перезапускать отдельные сервисы без остановки всей инфраструктуры
> - Использовать hot-reload для быстрой итерации
> - Применять миграции независимо для каждого сервиса

**Важно:** Перед запуском сервисов убедитесь, что:
1. Инфраструктура (PostgreSQL + Redis) запущена
2. Миграции применены для каждого сервиса (см. ниже)

**Gateway Service:**
```bash
# 1. Применить миграции (если еще не применены)
cd gateway-service
source venv-gateway/bin/activate
alembic upgrade head

# 2. Запустить сервис
# Вариант A: Docker
cd ../infrastructure
docker-compose -f docker-compose.gateway.yml up -d

# Вариант B: Локально (рекомендуется для разработки)
cd ../gateway-service
source venv-gateway/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# Проверить
curl http://localhost:8080/health
```

**Odds Service:**
```bash
# 1. Применить миграции (если еще не применены)
cd odds-service
source venv-odds/bin/activate
alembic upgrade head

# 2. Запустить сервисы
# Вариант A: Docker (API + Worker + Scheduler)
cd ../infrastructure
docker-compose -f docker-compose.odds.yml up -d

# Вариант B: Локально (рекомендуется для разработки)
cd ../odds-service
source venv-odds/bin/activate

# В отдельных терминалах:
# Терминал 1: API Server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8083

# Терминал 2: Worker
python -m boot.worker

# Терминал 3: Scheduler (опционально, если нужен автоматический запуск)
python -m boot.scheduler

# Проверить
curl http://localhost:8083/health

# Ручной запуск сбора данных
curl -X POST http://localhost:8083/_admin/tasks/collect \
  -H "Authorization: Bearer <admin_token>"
```

**Edge Agents Service:**
```bash
# 1. Применить миграции (если используются)
cd edge-agents-service
source venv-agents/bin/activate
# alembic upgrade head  # если используется Alembic

# 2. Запустить сервис
# Вариант A: Docker
cd ../infrastructure
docker-compose -f docker-compose.agents.yml up -d

# Вариант B: Локально (рекомендуется для разработки)
cd ../edge-agents-service
source venv-agents/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8082

# Проверить
curl http://localhost:8082/health
```

### Локальная разработка (без Docker)

**1. Настроить базу данных и Redis:**
```bash
# Вариант A: Использовать Docker только для инфраструктуры
cd infrastructure

# Для инфраструктуры можно использовать env.example (если есть):
# cp .env.example .env

# Создать Docker network
docker network create layerbit-net 2>/dev/null || true

# Запустить инфраструктуру
docker-compose -f docker-compose.infra.yml up -d

# Вариант B: Локальная установка PostgreSQL и Redis
# Установить PostgreSQL 15 и Redis 7 локально
```

**2. Применить миграции баз данных:**
```bash
# Важно: Применяйте миграции ДО запуска сервисов

# Gateway Service миграции
cd gateway-service
source venv-gateway/bin/activate  # или создайте виртуальное окружение
pip install -r requirements.txt
alembic upgrade head
alembic current  # проверить текущую версию

# Odds Service миграции
cd ../odds-service
source venv-odds/bin/activate  # или создайте виртуальное окружение
pip install -r requirements.txt
alembic upgrade head
alembic current  # проверить текущую версию

# Edge Agents Service миграции (если используются)
# cd ../edge-agents-service
# source venv-agents/bin/activate
# pip install -r requirements.txt
# alembic upgrade head  # если используется Alembic
```

**3. Запустить сервисы:**

**Frontend:**
```bash
cd frontend/oraculum-dashboard
npm install
npm run dev  # http://localhost:5173
```

**Gateway Service:**
```bash
cd gateway-service
source venv-gateway/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# Или через VS Code: используйте конфигурацию из .vscode/launch.json
```

**Odds Service:**
```bash
cd odds-service
source venv-odds/bin/activate

# В отдельных терминалах:

# 1. API Server
python -m app.main
# или
uvicorn app.main:app --reload --host 0.0.0.0 --port 8083

# 2. Worker (обработка задач)
python -m boot.worker

# 3. Scheduler (cron задачи)
python -m boot.scheduler
```

**Edge Agents Service:**
```bash
cd edge-agents-service
source venv-agents/bin/activate  # создайте виртуальное окружение
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8082
```

### Остановка сервисов

```bash
# Остановить все сервисы
cd infrastructure
docker-compose down

# Остановить конкретный сервис
docker-compose -f docker-compose.odds.yml down

# Остановить с удалением volumes (⚠️ удалит данные!)
docker-compose down -v
```

### Проверка работоспособности

```bash
# Health checks
curl http://localhost:8080/health  # Gateway
curl http://localhost:8083/health   # Odds API
curl http://localhost:8082/health  # Edge Agents

# Metrics (Prometheus)
curl http://localhost:8080/metrics  # Gateway
curl http://localhost:8083/metrics  # Odds API

# База данных
psql -h localhost -U postgres -d layerbit -c "SELECT COUNT(*) FROM users;"
psql -h localhost -U postgres -d layerbit -c "SELECT COUNT(*) FROM sports;"

# Redis
redis-cli ping
redis-cli keys "*"
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
