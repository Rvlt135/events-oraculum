# Layerbit-Oraculum-AI Backend MVP

AI-система "оракулов" для анализа беттинговых событий. MVP фокусируется на футбольных событиях (UEFA Champions League) с модульной архитектурой микросервисов.

## Архитектура: Services-First

Каждый сервис **полностью независим** и готов к выносу в отдельный репозиторий без изменений. Монорепозиторий — временная организационная структура.

### Этапы разработки

**Этап 1 (Завершён):**
1. ✅ **odds-service** - Сбор, нормализация и хранение данных

**Этап 2 (Завершён):**
2. ✅ **edge-agents-service** - AI-агенты для анализа и рекомендаций

**Этап 3 (Завершён):**
3. ✅ **gateway-service** - Публичное API для выдачи инсайтов

## Структура проекта

```
layerbit-oraculs-bet/
├── odds-service/              # Этап 1 - Независимый сервис
│   ├── app/
│   │   ├── admin_api/        # FastAPI эндпоинты
│   │   ├── tasks/            # TaskIQ таски (collector, normalizer)
│   │   ├── domain/           # Pydantic модели (Event, Market, Quote)
│   │   ├── adapters/         # the_odds_api.py (внешний API)
│   │   ├── infra/            # redis_client.py, pg_client.py
│   │   └── config/           # settings.py
│   ├── boot/                 # worker.py, scheduler.py, admin_api.py
│   ├── db/
│   │   └── schema.sql
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── edge-agents-service/      # Этап 2 - AI-агенты
│   ├── app/
│   │   ├── config/           # settings.py
│   │   ├── models/           # recommendation.py (SQLAlchemy)
│   │   ├── db/               # pg.py, repositories.py
│   │   ├── services/         # features.py, runner.py, agents/
│   │   ├── routes/           # internal.py (/_agents/*)
│   │   └── main.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── gateway-service/          # Этап 3 - Публичное API
│   ├── app/
│   │   ├── config/           # settings.py
│   │   ├── models/           # schemas.py (DTOs)
│   │   ├── db/               # pg.py, repositories.py (read-only)
│   │   ├── cache/            # redis.py
│   │   ├── security/         # apikey.py
│   │   ├── services/         # insights_service.py, stats_service.py
│   │   ├── routes/           # insights.py, stats.py
│   │   └── main.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
└── infrastructure/           # Docker Compose
    ├── docker-compose.yml
    └── README.md
```

## Этап 1: odds-service

### Возможности
- Сбор коэффициентов из The Odds API (UEFA Champions League)
- Нормализация названий команд
- Агрегация коэффициентов (avg, best)
- Автоматический сбор 2 раза в сутки (9:00, 19:00)
- Admin API для ручного запуска и просмотра данных
- Prometheus метрики

### Admin API Endpoints

**POST /_admin/tasks/collect**
- Ручной запуск сбора данных
- Ставит задачу в очередь TaskIQ

**GET /_admin/data/snapshots?limit=100&league=soccer_uefa_champs_league**
- Просмотр нормализованных снэпшотов
- Данные с временными метками (ts_src, ts_ingest)

**GET /health**
- Health check

**GET /metrics**
- Prometheus метрики

## Быстрый старт

### Используя Docker Compose (Рекомендуется)

1. Настроить odds-service:
```bash
cd odds-service
cp .env.example .env
# Отредактировать .env - добавить ODDS_API_KEY
```

2. Запустить все сервисы:
```bash
cd infrastructure
docker-compose up -d
```

3. Проверить API:
```bash
# Health check
curl http://localhost:8081/health

# Запустить сбор вручную
curl -X POST http://localhost:8081/_admin/tasks/collect

# Просмотреть снэпшоты
curl http://localhost:8081/_admin/data/snapshots?limit=10
```

### Запущенные сервисы

- **gateway**: http://localhost:8080 (Публичное API)
- **odds-admin-api**: http://localhost:8081 (Internal)
- **odds-worker**: Обработчик фоновых задач
- **odds-scheduler**: Планировщик (cron: 9:00, 19:00)
- **edge-agents**: http://localhost:8082 (Internal AI)
- **postgres**: localhost:5432
- **redis**: localhost:6379

## База данных

Схема автоматически инициализируется из `odds-service/db/schema.sql`.

Таблицы:
- `sports` - Справочник видов спорта
- `leagues` - Лиги/соревнования
- `teams` - Команды с нормализованными названиями
- `events` - Беттинговые события
- `bookmakers` - Справочник букмекеров
- `odds_snapshots` - Сырые данные с ts_src, ts_ingest
- `normalized_odds` - Агрегированная статистика
- `recommendations` - Рекомендации от AI-агентов

## Поток данных

1. **Scheduler** запускает задачу сбора (cron или вручную)
2. **Worker** забирает задачу из очереди Redis
3. **API Adapter** получает данные из The Odds API
4. **Normalizer** обрабатывает и трансформирует данные
5. **PG Client** сохраняет сырые снэпшоты и нормализованные коэффициенты
6. **Admin API** предоставляет доступ к данным

## Технологический стек

- **Python 3.12+**
- **FastAPI** - Web framework
- **TaskIQ** - Очередь задач и планировщик
- **PostgreSQL 15** - Персистентное хранилище
- **Redis 7** - Очередь и кэш
- **HTTPX** - Async HTTP клиент
- **Pydantic v2** - Валидация данных
- **Prometheus** - Метрики
- **structlog** - Структурированное логирование

## Этап 2: edge-agents-service

### Возможности
- Анализ нормализованных данных через LLM
- Интеграция с OpenRouter API (LiteLLM, LangChain)
- Генерация рекомендаций (pick, confidence, explanation)
- Extensible архитектура агентов (готовность к voting)

### API Endpoints

**POST /_agents/run_batch**
- Запуск анализа для событий
- Параметры: event_ids, league, from_date, to_date

**GET /_agents/recommendations**
- Получение рекомендаций
- Фильтры: league, from, to, min_conf

**GET /_agents/health**
- Health check

**Пример использования:**
```bash
# Запустить анализ для лиги
curl -X POST http://localhost:8082/_agents/run_batch \
  -H "Content-Type: application/json" \
  -d '{"league": "soccer_uefa_champs_league"}'

# Получить рекомендации
curl "http://localhost:8082/_agents/recommendations?league=soccer_uefa_champs_league&min_conf=0.6"
```

## Этап 3: gateway-service

### Возможности
- Публичное REST API для чтения рекомендаций
- API-key аутентификация
- Redis кеширование
- Пагинация и фильтрация
- Prometheus метрики

### API Endpoints

**GET /v1/insights/recommendations**
- Получение рекомендаций с пагинацией
- Фильтры: league, from, to, min_conf
- Требуется: X-API-Key

**GET /v1/insights/events/{event_id}**
- Детали события с рекомендациями и odds контекстом
- Требуется: X-API-Key

**GET /v1/stats/summary**
- Базовая статистика рекомендаций
- Фильтры: league, from, to
- Требуется: X-API-Key

**Пример использования:**
```bash
# Установить API-key в .env
echo "API_KEY=my_secure_key" >> gateway-service/.env

# Получить рекомендации
curl -X GET "http://localhost:8080/v1/insights/recommendations?league=soccer_uefa_champs_league&limit=10" \
  -H "X-API-Key: my_secure_key"

# Получить статистику
curl -X GET "http://localhost:8080/v1/stats/summary?league=soccer_uefa_champs_league" \
  -H "X-API-Key: my_secure_key"
```

## Архитектура системы

### Поток данных

1. **odds-service** собирает данные из The Odds API → PostgreSQL
2. **edge-agents-service** анализирует через LLM → recommendations в PostgreSQL
3. **gateway-service** читает из PostgreSQL/Redis → Публичное API

### Взаимодействие сервисов

- Сервисы взаимодействуют только через PostgreSQL
- Нет прямых HTTP запросов между сервисами
- Каждый сервис полностью независим
- Redis используется для кеширования (опционально)

## Принципы разработки

- Каждый сервис имеет собственный Dockerfile и requirements.txt
- Отсутствует shared-код между сервисами (готовность к экстракции)
- Сервисы взаимодействуют только через базу данных
- Каждый сервис развертывается независимо
- SOLID, DRY, KISS
