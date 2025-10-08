# Этап 3 завершён: gateway-service

## Реализовано

Создан публичный backend-сервис для выдачи беттинговых рекомендаций и статистики через REST API.

### Архитектурные особенности

**Read-Only Gateway Pattern:**
- Сервис только читает данные из PostgreSQL/Redis
- Не обращается к внешним API
- Stateless архитектура
- Агрессивное кеширование

**Services-First Pattern:**
- Полностью независимый сервис
- Собственный Dockerfile, requirements.txt, конфигурация
- Готов к выносу в отдельный репозиторий

### Ключевые компоненты

**1. Public REST API (/v1)**
- `/v1/insights/recommendations` - Список рекомендаций с пагинацией
- `/v1/insights/events/{event_id}` - Детали события с контекстом
- `/v1/stats/summary` - Базовая статистика

**2. Security**
- API-key аутентификация через заголовок X-API-Key
- Middleware проверки на всех /v1/* эндпоинтах
- 401/403 ошибки при неверном ключе

**3. Caching Layer**
- Redis кеширование деталей событий
- Настраиваемый TTL (default: 5 минут)
- Автоматическая инвалидация

**4. Data Access**
- Read-only репозитории
- Оптимизированные SQL запросы
- Connection pooling (10 базовых + 20 overflow)

**5. DTOs**
- RecommendationDTO - рекомендация
- EventDTO - событие с контекстом
- OddsContextDTO - компактный контекст odds
- StatsDTO - статистика
- PaginatedResponse - пагинированный ответ

**6. Services Layer**
- InsightsService - use-cases для insights
- StatsService - use-cases для статистики
- Разделение бизнес-логики от routes

### Структура проекта

```
gateway-service/
├── app/
│   ├── config/settings.py           # Конфигурация
│   ├── models/schemas.py            # DTOs
│   ├── db/
│   │   ├── pg.py                    # Async session
│   │   └── repositories.py          # Read-only repos
│   ├── cache/redis.py               # Redis кеш
│   ├── security/apikey.py           # API-key validation
│   ├── services/
│   │   ├── insights_service.py
│   │   └── stats_service.py
│   ├── routes/
│   │   ├── insights.py              # /v1/insights/*
│   │   └── stats.py                 # /v1/stats/*
│   ├── observability/logging.py     # Structured logging
│   └── main.py                      # FastAPI app
├── Dockerfile
├── requirements.txt
└── .env.example
```

### Docker Compose

Добавлен контейнер `gateway`:
- Порт: 8080
- Зависит от postgres и redis
- Read-only доступ к данным

### API Examples

**1. Получить рекомендации:**
```bash
curl -X GET "http://localhost:8080/v1/insights/recommendations?league=soccer_uefa_champs_league&min_conf=0.6&limit=10" \
  -H "X-API-Key: my_secure_key"
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
      "short_explanation": "Strong home advantage",
      "model_version": "openai/gpt-4o-mini_betting_analysis_v1",
      "created_ts": "2025-10-08T10:30:00Z"
    }
  ]
}
```

**2. Получить детали события:**
```bash
curl -X GET "http://localhost:8080/v1/insights/events/{event_id}" \
  -H "X-API-Key: my_secure_key"
```

**Ответ:**
```json
{
  "event_id": "uuid",
  "league_key": "soccer_uefa_champs_league",
  "home_team": "Real Madrid",
  "away_team": "Bayern Munich",
  "commence_time": "2025-10-15T19:00:00Z",
  "recommendations": [...],
  "odds_context": {
    "home_odds_avg": 2.10,
    "away_odds_avg": 3.50,
    "bookmakers_count": 15
  }
}
```

**3. Получить статистику:**
```bash
curl -X GET "http://localhost:8080/v1/stats/summary?league=soccer_uefa_champs_league" \
  -H "X-API-Key: my_secure_key"
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
  "latest_recommendation_ts": "2025-10-08T12:00:00Z"
}
```

### Конфигурация

Основные переменные окружения:

**Security:**
- `API_KEY` - Ключ для аутентификации (обязательно)

**Database:**
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`

**Redis:**
- `REDIS_URL` - URL подключения
- `CACHE_TTL_SECONDS` - TTL кеша (default: 300)

**API:**
- `API_HOST` - Хост (default: 0.0.0.0)
- `API_PORT` - Порт (default: 8080)

**Pagination:**
- `DEFAULT_PAGE_LIMIT` - Лимит по умолчанию (default: 50)
- `MAX_PAGE_LIMIT` - Максимальный лимит (default: 500)

### Технологический стек

- Python 3.12+
- FastAPI
- SQLAlchemy (async)
- PostgreSQL 15
- Redis 7
- Pydantic v2
- structlog
- prometheus-client

### Observability

**Structured Logging:**
- JSON формат
- ISO timestamps
- Request/response tracking
- Error tracking

**Prometheus Metrics:**
- Доступны на `/metrics`
- HTTP request duration
- HTTP request count
- Custom business metrics (опционально)

**Health Checks:**
- `/health` - Service health
- Проверка доступности Redis/PostgreSQL (в будущем)

### Security Best Practices

**API-key Management:**
- Хранение через переменные окружения
- Никогда не коммитить в git
- Регулярная ротация ключей

**CORS:**
- Настраиваемые origins
- Не использовать `["*"]` в production

**Rate Limiting:**
- Рекомендуется для production
- Можно добавить на уровне nginx/traefik

### Boundaries (Что НЕ делает сервис)

- ❌ Не собирает данные из внешних API
- ❌ Не запускает AI-анализ
- ❌ Не модифицирует данные
- ✅ Только читает и форматирует данные
- ✅ Кеширует для ускорения
- ✅ Предоставляет публичное API

### Архитектура системы

**Полный поток данных:**

1. **odds-service** → The Odds API → PostgreSQL (события, коэффициенты)
2. **edge-agents-service** → LLM через OpenRouter → PostgreSQL (рекомендации)
3. **gateway-service** → PostgreSQL/Redis → Публичное API (чтение)

**Взаимодействие:**
- Сервисы не делают HTTP запросы друг к другу
- Единственная точка интеграции - PostgreSQL
- Redis опционально для кеша
- Полная независимость сервисов

### Масштабируемость

**Горизонтальное масштабирование:**
- Stateless сервис
- Можно запустить множество экземпляров
- Load balancer перед gateway
- Shared PostgreSQL и Redis

**Vertical scaling:**
- Connection pool настраивается
- Кеш снижает нагрузку на БД
- Оптимизированные SQL запросы

### Production Readiness

**Готово:**
- ✅ API-key аутентификация
- ✅ Structured logging
- ✅ Health checks
- ✅ Prometheus metrics
- ✅ Error handling
- ✅ Input validation
- ✅ Connection pooling
- ✅ Caching strategy

**Рекомендуется добавить:**
- Rate limiting
- Request ID tracking
- Distributed tracing (OpenTelemetry)
- Более детальные health checks
- Circuit breaker pattern

### Следующие шаги (опционально)

**Улучшения:**
1. Rate limiting middleware
2. Request ID для трейсинга
3. Circuit breaker для PostgreSQL/Redis
4. Более детальные метрики (per-endpoint)
5. Swagger UI документация (уже включено в FastAPI)
6. Websockets для real-time updates (если нужно)

**Масштабирование:**
1. Kubernetes deployment
2. Horizontal pod autoscaling
3. Read replicas для PostgreSQL
4. Redis cluster

### Validation Checklist

- ✅ Сервис поднимается на порту 8080
- ✅ GET /v1/stats/summary работает с API-KEY
- ✅ GET /v1/insights/recommendations возвращает пагинированный список
- ✅ GET /v1/insights/events/{event_id} возвращает детали
- ✅ API-KEY проверяется (401/403 без ключа)
- ✅ Redis кеширование работает
- ✅ Structured logging в JSON
- ✅ Prometheus metrics доступны

### Примечания

- Сервис полностью read-only
- Все модификации данных в других сервисах
- Готов к production deployment
- Горизонтально масштабируемый
- Следует принципам SOLID, DRY, KISS
