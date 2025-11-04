# Gateway Service Tests

Этот директорий содержит тесты для Gateway Service, организованные по типам и функциональности.

## Структура тестов

```
tests/
├── conftest.py                    # Общие фикстуры и конфигурация
├── unit/                          # Модульные тесты
│   ├── test_auth_schemas.py      # Тесты схем аутентификации
│   ├── test_insights_service.py  # Тесты сервиса инсайтов
│   ├── test_telegram_validator.py # Тесты Telegram валидатора
│   ├── test_redis_cache.py       # Тесты Redis кэша
│   └── test_jwt_utils.py         # Тесты JWT утилит
├── integration/                   # Интеграционные тесты
│   ├── test_auth_endpoints.py    # Тесты API аутентификации
│   ├── test_insights_endpoints.py # Тесты API инсайтов
│   └── test_stats_endpoints.py   # Тесты API статистики
└── fixtures/                      # Тестовые данные
```

## Запуск тестов

### Быстрый запуск

```bash
# Активируйте виртуальное окружение
source venv-gateway/bin/activate

# Запустите все тесты
python run_tests.py

# Запустите только модульные тесты
python run_tests.py unit

# Запустите только интеграционные тесты
python run_tests.py integration

# Запустите тесты с покрытием
python run_tests.py coverage

# Запустите тесты с HTML отчетом
python run_tests.py html
```

### Прямой запуск pytest

```bash
# Все тесты
pytest

# Модульные тесты
pytest tests/unit/

# Интеграционные тесты
pytest tests/integration/

# Конкретный файл
pytest tests/unit/test_auth_schemas.py

# Конкретный тест
pytest tests/unit/test_auth_schemas.py::TestTelegramInfo::test_telegram_info_creation

# С покрытием
pytest --cov=app --cov-report=term-missing

# С HTML отчетом
pytest --cov=app --cov-report=html:htmlcov
```

### Параметры pytest

```bash
# Подробный вывод
pytest -v

# Остановка на первой ошибке
pytest -x

# Запуск только измененных тестов
pytest --lf

# Запуск в параллельном режиме
pytest -n auto

# Запуск с профилированием
pytest --profile

# Запуск медленных тестов
pytest -m slow

# Пропуск медленных тестов
pytest -m "not slow"
```

## Типы тестов

### Модульные тесты (Unit Tests)

Тестируют отдельные компоненты в изоляции:

- **test_auth_schemas.py** - Тесты Pydantic схем для аутентификации
- **test_insights_service.py** - Тесты бизнес-логики сервиса инсайтов
- **test_telegram_validator.py** - Тесты валидации Telegram данных
- **test_redis_cache.py** - Тесты Redis кэширования
- **test_jwt_utils.py** - Тесты JWT токенов

### Интеграционные тесты (Integration Tests)

Тестируют взаимодействие между компонентами:

- **test_auth_endpoints.py** - Тесты API эндпоинтов аутентификации
- **test_insights_endpoints.py** - Тесты API эндпоинтов инсайтов
- **test_stats_endpoints.py** - Тесты API эндпоинтов статистики

## Фикстуры

### Основные фикстуры (conftest.py)

- `test_settings` - Настройки для тестов
- `test_db_url` - URL тестовой базы данных
- `test_engine` - Движок тестовой базы данных
- `test_db_session` - Сессия тестовой базы данных
- `mock_redis` - Мок Redis клиента
- `test_client` - FastAPI тестовый клиент
- `mock_jwt_service` - Мок JWT сервиса
- `mock_auth_service` - Мок сервиса аутентификации
- `sample_user_data` - Тестовые данные пользователя
- `sample_telegram_data` - Тестовые данные Telegram
- `sample_recommendation_data` - Тестовые данные рекомендаций
- `sample_event_data` - Тестовые данные событий

## Маркеры тестов

Тесты помечены маркерами для категоризации:

- `@pytest.mark.unit` - Модульные тесты
- `@pytest.mark.integration` - Интеграционные тесты
- `@pytest.mark.slow` - Медленные тесты
- `@pytest.mark.auth` - Тесты аутентификации
- `@pytest.mark.api` - Тесты API
- `@pytest.mark.database` - Тесты базы данных
- `@pytest.mark.redis` - Тесты Redis

## Покрытие кода

Цель покрытия: **80%**

Текущее покрытие можно посмотреть в:
- Консольном выводе при запуске с `--cov`
- HTML отчете в `htmlcov/index.html`

### Исключения из покрытия

Некоторые файлы могут быть исключены из расчета покрытия:
- `app/main.py` - Точка входа приложения
- `app/config/settings.py` - Конфигурация
- `alembic/` - Миграции базы данных

## Тестовые данные

### База данных

Тесты используют отдельную тестовую базу данных:
- **База**: `test_layerbit`
- **Пользователь**: `postgres`
- **Пароль**: `postgres`

### Redis

Тесты используют отдельную тестовую базу Redis:
- **База**: `1` (вместо `0` для продакшена)

## Настройка окружения

### Переменные окружения

Тесты автоматически настраивают тестовое окружение, но можно переопределить:

```bash
export TEST_DATABASE_URL="postgresql://user:pass@localhost/test_db"
export TEST_REDIS_URL="redis://localhost:6379/1"
```

### Зависимости

Все тестовые зависимости установлены в `requirements.txt`:
- `pytest` - Основной фреймворк тестирования
- `pytest-asyncio` - Поддержка асинхронных тестов
- `pytest-mock` - Моки и патчи
- `pytest-cov` - Покрытие кода
- `httpx` - HTTP клиент для тестов

## Отладка тестов

### Запуск с отладкой

```bash
# Запуск с pdb
pytest --pdb

# Запуск с подробным выводом
pytest -vvv

# Запуск конкретного теста с отладкой
pytest tests/unit/test_auth_schemas.py::TestTelegramInfo::test_telegram_info_creation --pdb
```

### Логирование

```bash
# Включить логи
pytest --log-cli-level=DEBUG

# Сохранить логи в файл
pytest --log-file=test.log --log-cli-level=DEBUG
```

### Проблемы и решения

1. **Ошибки импорта**
   ```bash
   # Убедитесь, что виртуальное окружение активировано
   source venv-gateway/bin/activate
   
   # Установите зависимости
   pip install -r requirements.txt
   ```

2. **Ошибки базы данных**
   ```bash
   # Создайте тестовую базу данных
   createdb test_layerbit
   
   # Примените миграции
   alembic upgrade head
   ```

3. **Ошибки Redis**
   ```bash
   # Запустите Redis
   redis-server
   
   # Или через Docker
   docker run -d --name redis-test -p 6379:6379 redis:7-alpine
   ```

## Непрерывная интеграция

### GitHub Actions

Пример конфигурации для GitHub Actions:

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_layerbit
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run tests
        run: |
          python run_tests.py coverage
```

## Лучшие практики

1. **Именование тестов**
   - Используйте описательные имена
   - Группируйте тесты по классам
   - Используйте `test_` префикс для функций

2. **Изоляция тестов**
   - Каждый тест должен быть независимым
   - Используйте фикстуры для настройки
   - Очищайте состояние после тестов

3. **Моки и стабы**
   - Мокайте внешние зависимости
   - Используйте `unittest.mock` для простых случаев
   - Используйте `pytest-mock` для сложных сценариев

4. **Асинхронные тесты**
   - Используйте `@pytest.mark.asyncio`
   - Правильно обрабатывайте async/await
   - Тестируйте как успешные, так и ошибочные сценарии

5. **Покрытие кода**
   - Стремитесь к высокому покрытию
   - Тестируйте граничные случаи
   - Не тестируйте тривиальный код
