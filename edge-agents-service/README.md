# Edge Agents Service

AI-агенты для анализа нормализованных беттинговых данных. Сервис использует LLM (через OpenRouter API) для генерации рекомендаций по футбольным событиям.

## Структура проекта

```
edge-agents-service/
├── app/
│   ├── config/
│   │   └── settings.py        # Конфигурация (pydantic-settings)
│   ├── models/
│   │   └── recommendation.py  # SQLAlchemy модели
│   ├── db/
│   │   ├── pg.py             # PostgreSQL async session
│   │   └── repositories.py   # CRUD для рекомендаций
│   ├── services/
│   │   ├── features.py       # Feature builder (h2h)
│   │   ├── runner.py         # Оркестрация анализа
│   │   └── agents/
│   │       ├── base.py       # Интерфейс Agent
│   │       └── llm_openrouter.py  # Реализация через OpenRouter
│   ├── routes/
│   │   └── internal.py       # FastAPI роуты /_agents/*
│   └── main.py               # FastAPI приложение
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Возможности

- Анализ нормализованных данных из odds-service
- Генерация рекомендаций через LLM (pick, confidence, explanation)
- Сохранение рекомендаций в PostgreSQL
- Extensible архитектура агентов (готовность к voting/ensembling)
- Внутреннее API для запуска анализа

## API Endpoints

### POST /_agents/run_batch
Запустить анализ для событий.

**Параметры:**
- `event_ids` (optional) - Список UUID событий
- `league` (optional) - Ключ лиги (например, `soccer_uefa_champs_league`)
- `from_date` (optional) - Начальная дата
- `to_date` (optional) - Конечная дата

**Пример:**
```bash
curl -X POST http://localhost:8082/_agents/run_batch \
  -H "Content-Type: application/json" \
  -d '{"league": "soccer_uefa_champs_league"}'
```

### GET /_agents/recommendations
Получить сохранённые рекомендации.

**Параметры:**
- `league` (optional) - Фильтр по лиге
- `from` (optional) - От даты
- `to` (optional) - До даты
- `min_conf` (optional) - Минимальная уверенность (0.0-1.0)
- `limit` (optional, default=100) - Лимит результатов

**Пример:**
```bash
curl "http://localhost:8082/_agents/recommendations?league=soccer_uefa_champs_league&min_conf=0.6&limit=10"
```

### GET /_agents/health
Health check.

```bash
curl http://localhost:8082/_agents/health
```

## Модель данных

### Recommendation
- `rec_id` (UUID) - Уникальный ID рекомендации
- `event_id` (UUID) - ID события
- `league_key` (string) - Ключ лиги
- `pick` (string) - Рекомендация (home/draw/away)
- `confidence` (float) - Уверенность (0.0-1.0)
- `short_explanation` (text) - Краткое объяснение
- `model_version` (string) - Версия модели
- `created_ts` (datetime) - Время создания

## Архитектура агентов

### Agent Interface
Абстракция `Agent` с методом `analyze()` позволяет легко добавлять новые агенты:
- `BaseLLMAgent` - Базовый LLM-агент
- `OpenRouterLLMAgent` - Реализация через OpenRouter API

В будущем можно добавить:
- Несколько агентов с разными моделями
- Voting/ensembling между агентами
- Специализированные агенты для разных лиг

## Конфигурация

Основные переменные окружения:

**LLM Settings:**
- `LLM_PROVIDER` - Провайдер (openrouter/litellm/langchain)
- `OPENROUTER_API_KEY` - API ключ OpenRouter (обязательно)
- `OPENROUTER_MODEL` - Модель (default: openai/gpt-4o-mini)
- `LLM_TEMPERATURE` - Температура генерации (0.0-1.0)
- `LLM_MAX_TOKENS` - Макс токенов ответа

**Database:**
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`

**Redis:**
- `REDIS_URL`

## Запуск через Docker Compose

```bash
cd infrastructure
docker-compose up -d edge-agents
```

## Локальная разработка

1. Установить зависимости:
```bash
pip install -r requirements.txt
```

2. Настроить .env:
```bash
cp .env.example .env
# Отредактировать .env - добавить OPENROUTER_API_KEY
```

3. Запустить:
```bash
python -m app.main
```

## Поток данных

1. **Feature Builder** читает нормализованные данные из PostgreSQL
2. **Agent** формирует prompt на основе фич (h2h odds)
3. **LLM** генерирует анализ и рекомендацию
4. **Repository** сохраняет результат в таблицу `recommendations`
5. Результаты доступны через GET /_agents/recommendations

## Расширяемость

- **Новые провайдеры**: Добавить реализацию Agent для других LLM
- **Новые фичи**: Расширить Feature Builder (например, историческая статистика)
- **Voting**: Запускать несколько агентов и агрегировать результаты
- **Кеширование**: Использовать Redis для кеширования промежуточных данных

## Технологический стек

- Python 3.12+
- FastAPI
- SQLAlchemy (async)
- PostgreSQL 15
- Redis 7
- LiteLLM / LangChain
- OpenRouter API
- Pydantic v2
- structlog
