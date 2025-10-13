# Odds Service

Сервис сбора и нормализации данных о беттинговых коэффициентах. Собирает данные из The Odds API, нормализует их в канонический формат (Event/Market/Quote) и предоставляет admin API для мониторинга.

## Структура проекта

```
odds-service/
├── app/
│   ├── admin_api/         # FastAPI эндпоинты для администрирования
│   │   └── app.py
│   ├── tasks/             # TaskIQ таски
│   │   ├── broker.py      # TaskIQ broker
│   │   ├── collector.py   # Задача сбора данных
│   │   └── normalizer.py  # Нормализация данных
│   ├── domain/            # Pydantic модели
│   │   └── models.py      # Event, Market, Quote, NormalizedSnapshot
│   ├── adapters/          # Внешние API
│   │   └── the_odds_api.py
│   ├── infra/             # Инфраструктурные клиенты
│   │   ├── redis_client.py
│   │   └── pg_client.py   # PostgreSQL клиент
│   └── config/
│       └── settings.py    # Конфигурация (pydantic-settings)
├── boot/                  # Точки входа
│   ├── admin_api.py       # Запуск admin API
│   ├── worker.py          # Запуск TaskIQ worker
│   └── scheduler.py       # Запуск TaskIQ scheduler
├── db/
│   └── schema.sql         # SQL схема базы данных
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Возможности

- Автоматический сбор коэффициентов из The Odds API (2 раза в сутки: 9:00, 19:00)
- Нормализация названий команд для консистентного сопоставления
- Агрегация коэффициентов (средние, лучшие)
- Admin API для ручного запуска и просмотра данных
- Prometheus метрики
- PostgreSQL для хранения
- Redis для очереди задач

## Admin API Endpoints

**POST /_admin/tasks/collect**
- Ручной запуск сбора данных
- Ставит задачу в очередь TaskIQ

**GET /_admin/data/snapshots?limit=100&league=soccer_uefa_champs_league**
- Просмотр нормализованных данных (Event/Market/Quote с ts_src, ts_ingest)
- Фильтрация по лиге

**GET /health**
- Health check

**GET /metrics**
- Prometheus метрики

## Запуск через Docker Compose

```bash
cd ../infrastructure
docker-compose up -d
```

## Локальная разработка

1. Установить зависимости:
```bash
pip install -r requirements.txt
```

2. Настроить .env:
```bash
cp .env.example .env
# Отредактировать .env - добавить ODDS_API_KEY
```

3. Запустить компоненты:
```bash
# Admin API
python -m boot.admin_api

# Worker (отдельный терминал)
python -m boot.worker

# Scheduler (отдельный терминал)
python -m boot.scheduler
```
```commandline
taskiq worker app.tasks.broker:broker app.tasks.collector
```
## Конфигурация

Основные переменные окружения:
- `ODDS_API_KEY` - Ключ The Odds API (обязательно)
- `ODDS_API_LEAGUES` - Список лиг для сбора
- `SCHEDULE_CRONS` - Расписание сбора (cron)
- `REDIS_URL` - Подключение к Redis
- `POSTGRES_*` - Параметры PostgreSQL

## Модель данных

### Event
Беттинговое событие с командами, временем начала и статусом.

### Market
Тип рынка (h2h, spreads, totals) с исходами.

### Quote
Коэффициенты букмекера с временными метками:
- `ts_src` - От API провайдера
- `ts_ingest` - Когда получено сервисом

### NormalizedSnapshot
Агрегированная статистика по событию:
- Средние коэффициенты (дом/выезд/ничья)
- Лучшие коэффициенты
- Количество букмекеров
