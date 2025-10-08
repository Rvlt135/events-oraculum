# Edge Agents Service

AI-агенты для анализа нормализованных беттинговых данных. Сервис использует LLM через AsyncOpenAI + instructor для генерации строго типизированных рекомендаций по футбольным событиям.

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
│   │   ├── clients/          # LLM клиенты
│   │   │   ├── base.py       # Интерфейс BaseLLMClient
│   │   │   ├── factory.py    # Фабрика клиентов
│   │   │   ├── openai_instructor.py  # AsyncOpenAI + instructor
│   │   │   ├── langchain_client.py   # LangChain адаптер
│   │   │   └── litellm_client.py     # LiteLLM адаптер
│   │   ├── prompts/          # Система промптов
│   │   │   ├── loader.py     # Загрузчик YAML промптов
│   │   │   └── processor.py  # Обработчик промптов
│   │   └── agents/
│   │       ├── base.py       # Интерфейс Agent
│   │       └── llm_agent.py  # LLM Agent с DI клиента
│   ├── routes/
│   │   └── internal.py       # FastAPI роуты /_agents/*
│   └── main.py               # FastAPI приложение
├── prompts/                   # YAML шаблоны промптов
│   ├── betting_analysis.yml
│   ├── conservative_analysis.yml
│   └── value_hunting.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Возможности

- **AsyncOpenAI + instructor** - строгая Pydantic-валидация ответов LLM
- **Выбор клиента** - instructor (default), LangChain, LiteLLM через настройки
- **YAML-конфигурация моделей** - models.yaml с параметрами моделей
- **Система YAML-промптов** - гибкое управление промптами через файлы
- Множественные стратегии анализа (betting_analysis, conservative_analysis, value_hunting)
- Extensible архитектура агентов (готовность к voting/ensembling)
- Анализ нормализованных данных из odds-service
- Сохранение рекомендаций в PostgreSQL
- Внутреннее API для запуска анализа

## API Endpoints

### POST /_agents/run_batch
Запустить анализ для событий.

**Параметры:**
- `event_ids` (optional) - Список UUID событий
- `league` (optional) - Ключ лиги (например, `soccer_uefa_champs_league`)
- `from_date` (optional) - Начальная дата
- `to_date` (optional) - Конечная дата
- `prompt_template` (optional, default: "betting_analysis") - Имя YAML шаблона промпта

**Примеры:**
```bash
# Использовать стандартный промпт
curl -X POST "http://localhost:8082/_agents/run_batch?league=soccer_uefa_champs_league"

# Использовать консервативный промпт
curl -X POST "http://localhost:8082/_agents/run_batch?league=soccer_uefa_champs_league&prompt_template=conservative_analysis"

# Использовать агрессивный промпт для поиска value
curl -X POST "http://localhost:8082/_agents/run_batch?league=soccer_uefa_champs_league&prompt_template=value_hunting"
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

### GET /_agents/prompts
Получить список доступных YAML промптов.

```bash
curl http://localhost:8082/_agents/prompts
```

**Ответ:**
```json
{
  "betting_analysis": "Main prompt for football match betting analysis",
  "conservative_analysis": "Conservative betting analysis with focus on value and risk",
  "value_hunting": "Aggressive value hunting focused on finding market inefficiencies"
}
```

### POST /_agents/prompts/reload
Перезагрузить YAML промпты без перезапуска сервиса.

```bash
curl -X POST http://localhost:8082/_agents/prompts/reload
```

## Архитектура LLM-клиентов

### AsyncOpenAI + instructor (Рекомендуется)

Сервис использует официальный AsyncOpenAI SDK, обёрнутый в instructor для строгой Pydantic-валидации:

```python
# Инициализация
client = AsyncOpenAI(
    api_key=settings.openrouter_api_key,
    base_url=settings.openrouter_base_url,
    max_retries=settings.openrouter_max_retries,
    default_headers={
        "HTTP-Referer": settings.openrouter_referer,
        "X-Title": settings.openrouter_app_title,
    }
)
instructor_client = instructor.from_openai(client)

# Генерация с Pydantic-схемой
response = await instructor_client.chat.completions.create(
    model="openai/gpt-4o-mini",
    messages=[...],
    response_model=RecommendationSchema  # Pydantic model
)
```

**Преимущества:**
- Строгая типизация ответов LLM
- Автоматическая валидация через Pydantic
- Поддержка JSON mode для совместимых моделей
- Retry логика из AsyncOpenAI
- Нет прямых httpx вызовов

### Выбор клиента

Сервис поддерживает переключение между клиентами через `LLM_CLIENT` в .env:

**instructor** (default):
```bash
LLM_CLIENT=instructor
```

**LangChain** (adapter stub):
```bash
LLM_CLIENT=langchain
```

**LiteLLM** (adapter stub):
```bash
LLM_CLIENT=litellm
```

### Конфигурация моделей

Модели настраиваются через `app/config/models.yaml`:

```yaml
models:
  - name: gpt-4o-mini
    provider: openrouter
    model_id: openai/gpt-4o-mini
    supports_json_mode: true
    max_context: 128000
    temperature_default: 0.7
    max_tokens_default: 500

default_model: gpt-4o-mini
```

**Выбор модели через настройки:**
```bash
ACTIVE_MODEL_NAME=gpt-4o-mini  # или gpt-4o, claude-3-5-sonnet, etc.
```

**Ключевые параметры:**
- `supports_json_mode` - использовать JSON mode если доступен
- `max_context` - максимальный размер контекста
- `temperature_default` - температура по умолчанию
- `max_tokens_default` - макс токенов по умолчанию

## Система YAML-промптов

Сервис использует гибкую систему промптов на основе YAML файлов, что позволяет:
- Легко изменять стратегии анализа без изменения кода
- Создавать множественные варианты промптов
- Версионировать промпты
- Настраивать параметры LLM (temperature, max_tokens) для каждого промпта

### Структура YAML промпта

```yaml
name: betting_analysis
version: "1.0"
description: "Описание промпта"

system_prompt: |
  Системный промпт для LLM

user_prompt_template: |
  Промпт с переменными {home_team}, {away_team}, {home_odds_avg}, etc.

response_format:
  type: "json"
  schema:
    pick:
      type: "string"
      enum: ["home", "draw", "away"]
    confidence:
      type: "number"
      minimum: 0.0
      maximum: 1.0

parameters:
  temperature: 0.7
  max_tokens: 500
  top_p: 0.9
```

### Доступные промпты

1. **betting_analysis** (по умолчанию)
   - Сбалансированный анализ
   - Temperature: 0.7
   - Подходит для общего использования

2. **conservative_analysis**
   - Консервативный подход
   - Temperature: 0.5
   - Фокус на минимизации рисков
   - Confidence ограничена до 0.7

3. **value_hunting**
   - Агрессивный поиск value
   - Temperature: 0.8
   - Фокус на market inefficiencies
   - Высокий риск / высокая награда

### Создание собственного промпта

1. Создайте YAML файл в директории `prompts/`:
```bash
touch prompts/my_custom_analysis.yml
```

2. Определите структуру промпта (см. примеры выше)

3. Перезагрузите промпты:
```bash
curl -X POST http://localhost:8082/_agents/prompts/reload
```

4. Используйте новый промпт:
```bash
curl -X POST "http://localhost:8082/_agents/run_batch?league=soccer_uefa_champs_league&prompt_template=my_custom_analysis"
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
