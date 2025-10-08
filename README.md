# Layerbit-Oraculum-AI Backend MVP

AI-система "оракулов" для анализа беттинговых событий. MVP фокусируется на футбольных событиях (UEFA Champions League) с модульной архитектурой микросервисов.

## Архитектура: Services-First

Каждый сервис **полностью независим** и готов к выносу в отдельный репозиторий без изменений. Монорепозиторий — временная организационная структура.

### Этапы разработки

**Этап 1 (Текущий):**
1. ✅ **odds-service** - Сбор, нормализация и хранение данных

**Этап 2 (Ожидает аппрува):**
2. **edge-agents-service** - AI-агенты для анализа и рекомендаций

**Этап 3 (Ожидает аппрува):**
3. **gateway-service** - Публичное API для выдачи инсайтов

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
├── edge-agents-service/      # Этап 2 (не создан)
├── gateway-service/          # Этап 3 (не создан)
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

- **odds-admin-api**: http://localhost:8081
- **odds-worker**: Обработчик фоновых задач
- **odds-scheduler**: Планировщик (cron: 9:00, 19:00)
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

## Следующие этапы

### Этап 2: edge-agents-service (Ожидает аппрува)
- Анализ через LLM-агенты
- Интеграция с OpenRouter API
- Генерация рекомендаций (pick, confidence, explanation)
- Сохранение результатов в PostgreSQL

### Этап 3: gateway-service (Ожидает аппрува)
- Публичное REST API
- Эндпоинты: /v1/insights/recommendations, /v1/stats/summary
- Доступ только на чтение к результатам анализа

## Принципы разработки

- Каждый сервис имеет собственный Dockerfile и requirements.txt
- Отсутствует shared-код между сервисами (готовность к экстракции)
- Сервисы взаимодействуют только через базу данных
- Каждый сервис развертывается независимо
- SOLID, DRY, KISS
