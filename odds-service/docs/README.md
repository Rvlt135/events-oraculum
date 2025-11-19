# Odds Service

Сервис для синхронизации данных о спортивных событиях и коэффициентах из внешних провайдеров.

## Локальный запуск

### 1. Настройка окружения

Создайте файл `.env` в корне проекта:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=layerbit

REDIS_URL=redis://localhost:6379/0
ODDS_API_KEY=your_api_key_here
ENVIRONMENT=development
LOG_LEVEL=INFO
API_PORT=8083
```

### 2. Запуск инфраструктуры

Если используется docker-compose из родительского репозитория:

```bash
# Из родительского репозитория
docker-compose up -d postgres redis
```

Или запустите контейнеры отдельно:

```bash
# PostgreSQL
docker run -d --name odds-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=layerbit \
  -p 5432:5432 \
  postgres:15-alpine

# Redis
docker run -d --name odds-redis \
  -p 6379:6379 \
  redis:7-alpine
```

### 3. Настройка Python окружения

```bash
python3.12 -m venv venv-odds
source venv-odds/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 4. Применение миграций

```bash
# Проверьте текущее состояние
alembic heads

# Примените миграции
alembic upgrade head
```

### 5. Запуск сервиса

```bash
# API сервер
uvicorn app.main:app --host 0.0.0.0 --port 8083 --reload

# Планировщик задач (в отдельном терминале)
python -m boot.scheduler

# Воркер задач (в отдельном терминале)
python -m boot.worker
```

## Работа с миграциями

### Основные команды

```bash
# Показать текущую ревизию в БД
alembic current

# Показать все head-ревизии (проверка на конфликты)
alembic heads

# Применить все миграции
alembic upgrade head

# Показать историю миграций
alembic history

# Создать новую миграцию (автогенерация)
alembic revision --autogenerate -m "description"

# Откатить одну миграцию
alembic downgrade -1
```

## Решение проблем с миграциями

### Multiple head revisions

Если при выполнении `alembic upgrade head` возникает ошибка:
```
ERROR: Multiple head revisions are present
```

**Причины:**
- Две миграции с одинаковым `revision` ID
- Две начальные миграции (обе с `down_revision = None`)
- Ветвление миграций без merge

**Решение:**

1. Проверьте heads:
```bash
alembic heads
```

2. Если есть дубликаты - удалите лишний файл из `alembic/versions/`

3. Если миграции разветвлены - создайте merge:
```bash
alembic merge heads -m "merge_branches"
```

4. Проверьте результат:
```bash
alembic heads  # должен быть только один head
```

### Миграции не применяются

1. Убедитесь, что БД создана:
```bash
docker exec -it odds-postgres psql -U postgres -c "CREATE DATABASE layerbit;"
```

2. Проверьте подключение:
```bash
docker exec -it odds-postgres psql -U postgres -d layerbit -c "SELECT 1;"
```

3. Если нужно сбросить (только для разработки):
```bash
docker exec -it odds-postgres psql -U postgres -d layerbit -c "DROP TABLE IF EXISTS alembic_version;"
alembic upgrade head
```


4. Запуск sheduler и worker TaskIQ 
# Scheduler
taskiq scheduler app.tasks.broker:scheduler

# Worker
taskiq worker app.tasks.broker:broker app.tasks.collector app.tasks.prioritizer


### Синхронизация миграций между разработчиками

1. Всегда делайте `git pull` перед созданием новой миграции
2. Все файлы миграций должны быть закоммичены в Git
3. На новом окружении всегда применяйте: `alembic upgrade head`

STRUCTURE:
odds-service/
└── app/
    ├── api/                      # Внешние интерфейсы (FastAPI)
    │   ├── http/                 # HTTP-роуты
    │   │   ├── admin.py          # /_admin/* (ручные триггеры)
    │   │   └── public.py         # /v1/* (если нужно)
    │   └── schemas/              # Pydantic схемы запрос/ответ (API boundary)
    │       ├── sports.py
    │       └── competitions.py
    │
    ├── domain/                     # Доменная модель (минимум, без «портов/юзкейсов»)
    │   ├── entities/             # ORM-агностичные сущности/DTO (не обяз. для MVP)
    │   │   ├── sport.py
    │   │   └── competition.py
    │   ├── rules/                # Бизнес-правила/валидаторы/политики (чистые функции)
    │   │   ├── visibility_policy.py
    │   │   └── window_policy.py
    │   └── types.py              # Общие типы/константы домена
    │
    ├── infrastructure/                     # Работа с данными (БД, кэш, внешние API)
    │   ├── db/
    │   │ . ├──orm/
    │   │   │  ├── sports.py
               ├──competition.py
    │   │   ├── orm.py            # SQLAlchemy модели (Sports, Competition, …)
    │   │   ├── engine.py         # create_async_engine, alembic bind
    │   │   └── session.py        # async_sessionmaker + helpers
    │   ├── repo/                 # Репозитории (тонкие, async)
    │   │   ├── sports_repo.py
    │   │   └── competitions_repo.py
    │   ├── cache/
    │   │   └── redis.py          # Client redis
    │   └── http/                 # Внешние клиенты
    │       ├── base_client.py    # базовый httpx клиент, retry/limiter
    │       └── odds_api.py       # The Odds API (sports, events, odds)
    │
    ├── services/                 # Прикладная логика (оркестрация шагов)
    │   ├── sports_service.py     # sync sports+competitions, обновление кэша
    │   └── events_service.py     # сбор events per provider_key (позже)
    │
    ├── worker/                     # Фоновые задачи (TaskIQ)
    │   ├── broker.py             # конфигурация брокера
    │   ├── worker.py             # entrypoint воркера
    │   └── schedule.py           # entrypoint планировщика (cron/LabelScheduleSource)
    │
    ├── config/                   # Настройки и политики
    │   ├── settings.py           # Pydantic Settings (.env)
    │   ├── provider_policy.yml   # YAML политика провайдера
    │   └── policy_loader.py      # загрузка→кэш в Redis, get_policy()
    │
    ├── app.py                    # FastAPI app + lifespan (DI, wiring)
    └── main.py                   # uvicorn entrypoint
