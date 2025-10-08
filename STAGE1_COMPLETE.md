# Этап 1 завершён: odds-service

## Реализовано

Создан полностью независимый backend-сервис для сбора и нормализации данных о беттинговых коэффициентах.

### Архитектурные особенности

**Паттерн Services-First:**
- Полностью независимый сервис (без shared-зависимостей)
- Собственный Dockerfile, requirements.txt, конфигурация
- Готов к выносу в отдельный репозиторий без изменений
- Самодостаточный со всеми объявленными зависимостями

### Ключевые компоненты

**1. Сбор данных**
- Интеграция с The Odds API
- Rate limiting и retry логика (tenacity, aiolimiter)
- Поддержка лиг (UEFA Champions League)
- Настраиваемые регионы и рынки

**2. Нормализация данных**
- Нормализация названий команд
- Агрегация коэффициентов (средние, лучшие)
- Временные метки: ts_src (API), ts_ingest (сервис), ts_normalized
- Канонический формат: Event → Market → Quote

**3. Управление задачами**
- TaskIQ для распределённой обработки
- Очередь на Redis
- Расписание сбора (cron: 9:00, 19:00)
- Поддержка ручного запуска

**4. Хранение**
- PostgreSQL для персистентных данных
- Автоинициализация схемы БД
- Таблицы: sports, leagues, teams, events, bookmakers, odds_snapshots, normalized_odds

**5. Admin API**
- **POST /_admin/tasks/collect** - Ручной запуск сбора
- **GET /_admin/data/snapshots** - Просмотр нормализованных данных (с фильтрами)
- **GET /health** - Health check
- **GET /metrics** - Prometheus метрики

**6. Observability**
- Prometheus метрики:
  - odds_collection_duration_seconds
  - odds_events_processed_total
  - odds_collection_errors_total
- Структурированное логирование (structlog, JSON)

### Структура проекта

```
odds-service/
├── app/
│   ├── admin_api/app.py                # Admin FastAPI эндпоинты
│   ├── tasks/
│   │   ├── broker.py                   # TaskIQ broker
│   │   ├── collector.py                # Задача сбора
│   │   └── normalizer.py               # Логика нормализации
│   ├── domain/models.py                # Domain модели
│   ├── adapters/the_odds_api.py        # The Odds API клиент
│   ├── infra/
│   │   ├── redis_client.py             # Redis клиент
│   │   └── pg_client.py                # PostgreSQL клиент
│   └── config/settings.py              # Конфигурация
├── boot/
│   ├── admin_api.py                    # Точка входа API сервера
│   ├── worker.py                       # Точка входа TaskIQ worker
│   └── scheduler.py                    # Точка входа TaskIQ scheduler
├── db/schema.sql                       # SQL схема
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

### Docker Compose

Расположение: `infrastructure/docker-compose.yml`

Сервисы:
- **redis** - Очередь задач и кэш (порт 6379)
- **postgres** - БД с автоинициализацией схемы (порт 5432)
- **odds-admin-api** - Admin API сервер (порт 8081)
- **odds-worker** - Обработчик фоновых задач
- **odds-scheduler** - Планировщик cron

### Как запустить

1. Настройка:
```bash
cd odds-service
cp .env.example .env
# Отредактировать .env - добавить ODDS_API_KEY
```

2. Запуск:
```bash
cd infrastructure
docker-compose up -d
```

3. Проверка:
```bash
curl http://localhost:8081/health
curl -X POST http://localhost:8081/_admin/tasks/collect
curl http://localhost:8081/_admin/data/snapshots?limit=10
```

### Конфигурация

Ключевые переменные окружения:
- `ODDS_API_KEY` - Ключ The Odds API (обязательно)
- `ODDS_API_LEAGUES` - Лиги для отслеживания
- `SCHEDULE_CRONS` - Расписание сбора
- `REDIS_URL` - Подключение к Redis
- `POSTGRES_*` - Параметры PostgreSQL

### Технологический стек

- Python 3.12+
- FastAPI
- TaskIQ + Redis
- PostgreSQL 15
- HTTPX (async HTTP)
- Pydantic v2
- Prometheus
- structlog
- tenacity (повторы)
- aiolimiter (rate limiting)

### Следующие шаги (Ожидают аппрува)

**Этап 2: edge-agents-service**
- AI-агенты для анализа
- Интеграция с OpenRouter API / LiteLLM
- Генерация рекомендаций (pick, confidence, explanation)
- Сохранение результатов в PostgreSQL

**Этап 3: gateway-service**
- Публичное REST API
- Эндпоинты: /v1/insights/recommendations, /v1/stats/summary
- Доступ только на чтение к результатам анализа

### Примечания

- Схема БД включает все необходимые таблицы с правильными индексами
- Сервис следует принципам SOLID, DRY, KISS
- Готов к горизонтальному масштабированию (stateless workers)
- Только backend (без фронтенда)
- Архитектура services-first (готовность к экстракции)
