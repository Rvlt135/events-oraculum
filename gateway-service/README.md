# Gateway Service

Публичное API для выдачи беттинговых рекомендаций и статистики. Сервис читает данные из PostgreSQL и Redis, которые заполняются odds-service и edge-agents-service.

## Структура проекта

```
gateway-service/
├── app/
│   ├── config/
│   │   └── settings.py        # Конфигурация (pydantic-settings)
│   ├── models/
│   │   └── schemas.py         # DTO для API
│   ├── db/
│   │   ├── pg.py             # PostgreSQL async session
│   │   └── repositories.py   # Read-only репозитории
│   ├── cache/
│   │   └── redis.py          # Redis кеш
│   ├── security/
│   │   └── apikey.py         # API-key проверка
│   ├── services/
│   │   ├── insights_service.py
│   │   └── stats_service.py
│   ├── routes/
│   │   ├── insights.py       # /v1/insights/*
│   │   └── stats.py          # /v1/stats/*
│   ├── observability/
│   │   └── logging.py        # Structured logging
│   └── main.py               # FastAPI приложение
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Возможности

- Публичное REST API для чтения рекомендаций
- Детальная информация по событиям с odds контекстом
- Базовая статистика качества рекомендаций
- API-key аутентификация
- Redis кеширование для ускорения
- Пагинация и фильтрация
- Structured logging (JSON)
- Prometheus метрики

## API Endpoints

### POST /v1/insights/recommendations
Получить список рекомендаций с пагинацией.

**Требуется:** API-key в заголовке `X-API-Key`

**Query параметры:**
- `league` (optional) - Фильтр по лиге (например, `soccer_uefa_champs_league`)
- `from` (optional) - Начальная дата (ISO 8601)
- `to` (optional) - Конечная дата (ISO 8601)
- `min_conf` (optional) - Минимальная уверенность (0.0-1.0)
- `limit` (optional, default: 50, max: 500) - Количество результатов
- `offset` (optional, default: 0) - Смещение для пагинации

**Пример:**
```bash
curl -X GET "http://localhost:8080/v1/insights/recommendations?league=soccer_uefa_champs_league&min_conf=0.6&limit=10" \
  -H "X-API-Key: your_api_key_here"
```

**Ответ:**
```json
{
  "total": 42,
  "limit": 10,
  "offset": 0,
  "items": [
    {
      "rec_id": "uuid",
      "event_id": "uuid",
      "league_key": "soccer_uefa_champs_league",
      "pick": "home",
      "confidence": 0.75,
      "short_explanation": "Strong home advantage with favorable odds",
      "model_version": "openai/gpt-4o-mini_betting_analysis_v1",
      "created_ts": "2025-10-08T10:30:00Z"
    }
  ]
}
```

### GET /v1/insights/events/{event_id}
Получить детали события с рекомендациями и odds контекстом.

**Требуется:** API-key в заголовке `X-API-Key`

**Пример:**
```bash
curl -X GET "http://localhost:8080/v1/insights/events/{event_id}" \
  -H "X-API-Key: your_api_key_here"
```

**Ответ:**
```json
{
  "event_id": "uuid",
  "external_id": "external_event_id",
  "league_key": "soccer_uefa_champs_league",
  "league_name": "UEFA Champions League",
  "home_team": "Real Madrid",
  "away_team": "Bayern Munich",
  "commence_time": "2025-10-15T19:00:00Z",
  "status": "upcoming",
  "recommendations": [
    {
      "rec_id": "uuid",
      "event_id": "uuid",
      "league_key": "soccer_uefa_champs_league",
      "pick": "home",
      "confidence": 0.75,
      "short_explanation": "Strong home advantage",
      "model_version": "openai/gpt-4o-mini_betting_analysis_v1",
      "created_ts": "2025-10-08T10:30:00Z"
    }
  ],
  "odds_context": {
    "home_odds_avg": 2.10,
    "away_odds_avg": 3.50,
    "draw_odds_avg": 3.20,
    "home_odds_best": 2.15,
    "away_odds_best": 3.60,
    "draw_odds_best": 3.30,
    "bookmakers_count": 15,
    "timestamp_source": "2025-10-08T09:00:00Z"
  }
}
```

### GET /v1/stats/summary
Получить базовую статистику рекомендаций.

**Требуется:** API-key в заголовке `X-API-Key`

**Query параметры:**
- `league` (optional) - Фильтр по лиге
- `from` (optional) - Начальная дата
- `to` (optional) - Конечная дата

**Пример:**
```bash
curl -X GET "http://localhost:8080/v1/stats/summary?league=soccer_uefa_champs_league" \
  -H "X-API-Key: your_api_key_here"
```

**Ответ:**
```json
{
  "count_recommendations": 156,
  "baseline_count": 78,
  "distribution_by_pick": {
    "home": 65,
    "draw": 31,
    "away": 60
  },
  "latest_recommendation_ts": "2025-10-08T12:00:00Z",
  "period_from": null,
  "period_to": null,
  "league_key": "soccer_uefa_champs_league"
}
```

### GET /health
Health check (без API-key).

```bash
curl http://localhost:8080/health
```

### GET /metrics
Prometheus метрики (без API-key).

```bash
curl http://localhost:8080/metrics
```

## Аутентификация

Все эндпоинты `/v1/*` требуют API-key в заголовке `X-API-Key`.

**Настройка API-key:**
```bash
# В .env файле
API_KEY=your_secure_api_key_here
```

**Использование:**
```bash
curl -H "X-API-Key: your_secure_api_key_here" http://localhost:8080/v1/insights/recommendations
```

**Ошибки:**
- `401 Unauthorized` - API-key отсутствует
- `403 Forbidden` - API-key неверный

## Кеширование

Сервис использует Redis для кеширования:
- Детали событий кешируются на 5 минут (по умолчанию)
- Автоматическая инвалидация при запросе свежих данных

**Настройка TTL:**
```bash
# В .env файле
CACHE_TTL_SECONDS=300
```

## Конфигурация

Основные переменные окружения:

**API Settings:**
- `API_HOST` - Хост (default: 0.0.0.0)
- `API_PORT` - Порт (default: 8080)
- `API_KEY` - Ключ для аутентификации (обязательно)

**Database:**
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`

**Redis:**
- `REDIS_URL` - URL подключения
- `CACHE_TTL_SECONDS` - TTL кеша (default: 300)

**Pagination:**
- `DEFAULT_PAGE_LIMIT` - Лимит по умолчанию (default: 50)
- `MAX_PAGE_LIMIT` - Максимальный лимит (default: 500)

**CORS:**
- `CORS_ORIGINS` - Разрешённые origins (default: ["*"])

## Запуск через Docker Compose

```bash
cd infrastructure
docker-compose up -d gateway
```

## Локальная разработка

1. Установить зависимости:
```bash
pip install -r requirements.txt
```

2. Настроить .env:
```bash
cp .env.example .env
# Отредактировать .env - установить API_KEY
```

3. Запустить:
```bash
python -m app.main
```

## Архитектура

### Слои

1. **Routes** - FastAPI эндпоинты
2. **Services** - Бизнес-логика (use-cases)
3. **Repositories** - Доступ к данным (read-only)
4. **DB/Cache** - PostgreSQL и Redis

### Принципы

- **Read-only** - Сервис только читает данные
- **No external APIs** - Не обращается к внешним API
- **Stateless** - Нет внутреннего состояния
- **Cacheable** - Агрессивное использование кеша
- **Secure** - API-key аутентификация

## Мониторинг

### Structured Logging

Все логи в JSON формате:
```json
{
  "event": "get_recommendations_request",
  "timestamp": "2025-10-08T10:30:00Z",
  "league": "soccer_uefa_champs_league",
  "limit": 50
}
```

### Prometheus Metrics

Доступны на `/metrics`:
- HTTP request duration
- HTTP request count
- Active connections
- Custom business metrics (опционально)

## Ограничения и производительность

- Максимальный лимит пагинации: 500
- Кеширование событий: 5 минут
- Connection pool: 10 базовых + 20 overflow
- Timeout БД: Automatic reconnect

## Технологический стек

- Python 3.12+
- FastAPI
- SQLAlchemy (async)
- PostgreSQL 15
- Redis 7
- Pydantic v2
- structlog
- prometheus-client

## Security Best Practices

1. **API-key хранение**
   - Никогда не коммитить в git
   - Использовать переменные окружения
   - Менять регулярно

2. **CORS**
   - Ограничить origins в production
   - Не использовать `["*"]` в production

3. **Rate Limiting**
   - Рекомендуется добавить для production
   - Можно использовать nginx/traefik на уровне reverse proxy
