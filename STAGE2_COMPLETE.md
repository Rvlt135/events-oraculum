# Этап 2 завершён: edge-agents-service

## Реализовано

Создан полностью независимый AI-сервис для анализа беттинговых данных и генерации рекомендаций через LLM.

### Архитектурные особенности

**Extensible Agent Architecture:**
- Абстракция `Agent` с интерфейсом для анализа
- Реализация `OpenRouterLLMAgent` через OpenRouter API
- Готовность к добавлению множественных агентов (voting/ensembling)
- Feature Builder для построения контекста из нормализованных данных

**Services-First Pattern:**
- Полностью независимый сервис
- Собственный Dockerfile, requirements.txt, конфигурация
- Готов к выносу в отдельный репозиторий

### Ключевые компоненты

**1. Feature Building**
- Чтение нормализованных данных из PostgreSQL
- Построение контекста для LLM (h2h market)
- Фильтрация событий по лиге и датам

**2. Agent System**
- `Agent` - Абстрактный интерфейс
- `OpenRouterLLMAgent` - Реализация через OpenRouter API
- Поддержка retry логики (tenacity)
- Парсинг и валидация ответов LLM

**3. Orchestration**
- `AgentRunner` - Оркестрация процесса анализа
- Batch processing событий
- Обработка ошибок и логирование

**4. Persistence**
- SQLAlchemy async модели
- Таблица `recommendations` с полями:
  - rec_id, event_id, league_key
  - pick (home/draw/away), confidence (0-1)
  - short_explanation, model_version
  - created_ts

**5. API**
- **POST /_agents/run_batch** - Запуск анализа
- **GET /_agents/recommendations** - Получение рекомендаций
- **GET /_agents/health** - Health check

### Структура проекта

```
edge-agents-service/
├── app/
│   ├── config/settings.py           # Конфигурация
│   ├── models/recommendation.py     # SQLAlchemy модели
│   ├── db/
│   │   ├── pg.py                    # Async session
│   │   └── repositories.py          # CRUD операции
│   ├── services/
│   │   ├── features.py              # Feature builder
│   │   ├── runner.py                # Оркестрация
│   │   └── agents/
│   │       ├── base.py              # Agent интерфейс
│   │       └── llm_openrouter.py    # OpenRouter реализация
│   ├── routes/internal.py           # FastAPI эндпоинты
│   └── main.py                      # FastAPI app
├── Dockerfile
├── requirements.txt
└── .env.example
```

### Docker Compose

Добавлен контейнер `edge-agents`:
- Порт: 8082
- Зависит от postgres и redis
- Автоинициализация таблицы recommendations

### Пример использования

1. Запустить анализ для лиги:
```bash
curl -X POST http://localhost:8082/_agents/run_batch \
  -H "Content-Type: application/json" \
  -d '{"league": "soccer_uefa_champs_league"}'
```

2. Получить рекомендации:
```bash
curl "http://localhost:8082/_agents/recommendations?league=soccer_uefa_champs_league&min_conf=0.6&limit=10"
```

3. Health check:
```bash
curl http://localhost:8082/_agents/health
```

### Конфигурация

Основные переменные окружения:
- `OPENROUTER_API_KEY` - Ключ API OpenRouter (обязательно)
- `OPENROUTER_MODEL` - Модель LLM (default: openai/gpt-4o-mini)
- `LLM_PROVIDER` - Провайдер (openrouter/litellm/langchain)
- `LLM_TEMPERATURE` - Температура генерации
- `LLM_MAX_TOKENS` - Максимум токенов
- `POSTGRES_*` - Параметры подключения к БД
- `REDIS_URL` - Подключение к Redis

### Технологический стек

- Python 3.12+
- FastAPI
- SQLAlchemy (async)
- PostgreSQL 15
- Redis 7
- LiteLLM
- LangChain
- OpenRouter API
- Pydantic v2
- structlog
- tenacity

### Поток данных

1. API получает запрос на анализ (event_ids или league)
2. Feature Builder извлекает нормализованные данные из БД
3. Agent формирует prompt с контекстом (команды, коэффициенты)
4. LLM генерирует анализ и рекомендацию
5. Результат валидируется и сохраняется в recommendations
6. Доступ к рекомендациям через GET /_agents/recommendations

### Расширяемость

**Готово к добавлению:**
- Множественных агентов с разными моделями
- Voting/ensembling механизмов
- Дополнительных фич (историческая статистика, форма команд)
- Других LLM провайдеров
- Кеширования промежуточных результатов

**Примеры расширения:**

1. Добавить нового агента:
```python
class CustomLLMAgent(Agent):
    async def analyze(self, features):
        # Custom logic
        pass
```

2. Voting между агентами:
```python
predictions = []
for agent in agents:
    pred = await agent.analyze(features)
    predictions.append(pred)

final_pick = vote(predictions)
```

### Следующие шаги (Ожидают аппрува)

**Этап 3: gateway-service**
- Публичное REST API
- Эндпоинты: /v1/insights/recommendations, /v1/stats/summary
- Кеширование
- Rate limiting
- Доступ только на чтение

### Примечания

- Сервис изолирован от odds-service
- Коммуникация только через PostgreSQL
- Готов к горизонтальному масштабированию
- Автоинициализация схемы БД через SQLAlchemy
- Следует принципам SOLID, DRY, KISS
