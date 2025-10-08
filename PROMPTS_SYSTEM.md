# Система YAML-промптов для edge-agents-service

## Обзор

Реализована гибкая система управления промптами через YAML файлы. Это позволяет:
- Изменять стратегии анализа без изменения кода
- Создавать множественные варианты промптов
- Версионировать промпты
- Настраивать параметры LLM индивидуально для каждого промпта
- Перезагружать промпты без перезапуска сервиса

## Архитектура

### Компоненты

1. **PromptLoader** (`app/services/prompts/loader.py`)
   - Загрузка YAML файлов из директории `prompts/`
   - Парсинг и валидация структуры
   - Кеширование промптов
   - Поддержка hot-reload

2. **PromptProcessor** (`app/services/prompts/processor.py`)
   - Подготовка контекста из features
   - Форматирование промпта с переменными
   - Расчет implied probabilities
   - Возврат готовых данных для LLM

3. **OpenRouterLLMAgent** (обновлен)
   - Принимает имя промпт-шаблона
   - Использует PromptProcessor для подготовки промпта
   - Передает параметры из YAML в LLM запрос

## Структура YAML промпта

```yaml
name: betting_analysis                    # Уникальное имя
version: "1.0"                           # Версия промпта
description: "Описание стратегии"        # Человекочитаемое описание

system_prompt: |                         # Системный промпт для LLM
  You are an expert sports betting analyst...

user_prompt_template: |                  # Шаблон с переменными
  Match: {home_team} vs {away_team}
  Odds: Home {home_odds_avg}, Away {away_odds_avg}
  ...

response_format:                         # Ожидаемый формат ответа
  type: "json"
  schema:
    pick:
      type: "string"
      enum: ["home", "draw", "away"]
    confidence:
      type: "number"
      minimum: 0.0
      maximum: 1.0
    explanation:
      type: "string"
      maxLength: 200

parameters:                              # Параметры LLM
  temperature: 0.7
  max_tokens: 500
  top_p: 0.9
```

## Доступные переменные в промпте

При форматировании `user_prompt_template` доступны следующие переменные:

- `{league_name}` - Название лиги
- `{home_team}` - Домашняя команда
- `{away_team}` - Гостевая команда
- `{commence_time}` - Время начала матча
- `{home_odds_avg}` - Средние коэффициенты на дом
- `{away_odds_avg}` - Средние коэффициенты на выезд
- `{draw_odds_avg}` - Средние коэффициенты на ничью
- `{home_odds_best}` - Лучшие коэффициенты на дом
- `{away_odds_best}` - Лучшие коэффициенты на выезд
- `{draw_odds_best}` - Лучшие коэффициенты на ничью
- `{bookmakers_count}` - Количество букмекеров
- `{home_probability}` - Implied probability для дома (%)
- `{draw_probability}` - Implied probability для ничьи (%)
- `{away_probability}` - Implied probability для выезда (%)

## Встроенные промпты

### 1. betting_analysis (по умолчанию)
**Файл:** `prompts/betting_analysis.yml`

**Характеристики:**
- Сбалансированный подход
- Temperature: 0.7
- Max tokens: 500
- Подходит для общего использования

**Стратегия:**
- Объективный анализ данных
- Фокус на implied probabilities
- Поиск market inefficiencies
- Консервативная уверенность

### 2. conservative_analysis
**Файл:** `prompts/conservative_analysis.yml`

**Характеристики:**
- Консервативный подход
- Temperature: 0.5 (более детерминистично)
- Max tokens: 400
- Confidence ограничена до 0.7

**Стратегия:**
- Приоритет risk management
- Рекомендации только при clear value
- Скептический подход к extreme odds
- Фокус на long-term profitability

### 3. value_hunting
**Файл:** `prompts/value_hunting.yml`

**Характеристики:**
- Агрессивный подход
- Temperature: 0.8 (более креативно)
- Max tokens: 600
- Полный диапазон confidence 0.0-1.0

**Стратегия:**
- Активный поиск value
- Фокус на odds discrepancies
- Contrarian positions
- Expected value (EV) calculation

## API для работы с промптами

### GET /_agents/prompts
Список всех доступных промптов с описаниями.

**Запрос:**
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
Перезагрузка промптов без перезапуска сервиса.

**Запрос:**
```bash
curl -X POST http://localhost:8082/_agents/prompts/reload
```

**Ответ:**
```json
{
  "status": "success",
  "message": "Prompts reloaded"
}
```

### POST /_agents/run_batch (с выбором промпта)
Запуск анализа с указанным промптом.

**Примеры:**
```bash
# Стандартный промпт
curl -X POST "http://localhost:8082/_agents/run_batch?league=soccer_uefa_champs_league"

# Консервативный
curl -X POST "http://localhost:8082/_agents/run_batch?league=soccer_uefa_champs_league&prompt_template=conservative_analysis"

# Value hunting
curl -X POST "http://localhost:8082/_agents/run_batch?league=soccer_uefa_champs_league&prompt_template=value_hunting"
```

## Создание кастомного промпта

### Шаг 1: Создать YAML файл
```bash
touch edge-agents-service/prompts/my_strategy.yml
```

### Шаг 2: Определить структуру
```yaml
name: my_strategy
version: "1.0"
description: "My custom analysis strategy"

system_prompt: |
  You are a specialized betting analyst...

user_prompt_template: |
  Analyze: {home_team} vs {away_team}
  Home odds: {home_odds_avg}
  Away odds: {away_odds_avg}

  Your custom instructions...

  Response format:
  {
      "pick": "home|draw|away",
      "confidence": 0.0-1.0,
      "explanation": "Brief reasoning"
  }

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
    explanation:
      type: "string"
      maxLength: 200

parameters:
  temperature: 0.6
  max_tokens: 450
  top_p: 0.95
```

### Шаг 3: Перезагрузить и использовать
```bash
# Перезагрузить
curl -X POST http://localhost:8082/_agents/prompts/reload

# Использовать
curl -X POST "http://localhost:8082/_agents/run_batch?league=soccer_uefa_champs_league&prompt_template=my_strategy"
```

## Версионирование model_version

При использовании разных промптов, версия модели автоматически включает имя промпта:

```
{model}_{prompt_template}_v1
```

Примеры:
- `openai/gpt-4o-mini_betting_analysis_v1`
- `openai/gpt-4o-mini_conservative_analysis_v1`
- `openai/gpt-4o-mini_value_hunting_v1`

Это позволяет отслеживать, какой промпт использовался для каждой рекомендации.

## Best Practices

1. **Тестирование промптов**
   - Тестируйте новые промпты на небольшой выборке
   - Сравнивайте результаты с baseline
   - Отслеживайте confidence и explanation

2. **Параметры LLM**
   - Temperature 0.5-0.7 для стабильных результатов
   - Temperature 0.7-0.9 для креативных стратегий
   - Max tokens 400-600 достаточно для анализа

3. **Версионирование**
   - Указывайте версию в YAML
   - При изменении промпта увеличивайте версию
   - Храните старые версии для сравнения

4. **Описания**
   - Используйте четкие description
   - Документируйте стратегию в comments
   - Указывайте use cases

## Логирование

Система промптов логирует:
- Загрузку промптов при старте
- Выбор промпта для анализа
- Параметры LLM из промпта
- Ошибки загрузки/парсинга

Пример лога:
```json
{
  "event": "prompt_loaded",
  "name": "betting_analysis",
  "version": "1.0",
  "file": "betting_analysis.yml"
}
```

## Расширение системы

### Добавление новых переменных

В `PromptProcessor._prepare_context()` можно добавить новые переменные:

```python
context["new_variable"] = calculate_new_metric(features)
```

### Добавление валидации

В `PromptLoader` можно добавить валидацию schema:

```python
def _validate_prompt(self, data: dict) -> bool:
    required_fields = ["name", "system_prompt", "user_prompt_template"]
    return all(field in data for field in required_fields)
```

### A/B тестирование

Можно запускать несколько промптов параллельно и сравнивать результаты:

```python
for template in ["betting_analysis", "conservative_analysis", "value_hunting"]:
    runner = AgentRunner(repository, prompt_template=template)
    result = await runner.run_batch(event_ids=[event_id])
```
