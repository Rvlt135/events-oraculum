# Alembic Database Migrations

Этот проект использует Alembic для управления миграциями базы данных.

## Установка зависимостей

```bash
# Активируйте виртуальное окружение
source venv-gateway/bin/activate

# Установите зависимости (включая Alembic)
pip install -r requirements.txt
```

## Основные команды

### Просмотр текущего состояния
```bash
alembic current
```

### Просмотр истории миграций
```bash
alembic history
```

### Создание новой миграции
```bash
# Автоматическое создание на основе изменений в моделях
alembic revision --autogenerate -m "Описание изменений"

# Ручное создание пустой миграции
alembic revision -m "Описание изменений"
```

### Применение миграций
```bash
# Применить все миграции до последней
alembic upgrade head

# Применить миграции до конкретной версии
alembic upgrade <revision_id>

# Применить следующую миграцию
alembic upgrade +1
```

### Откат миграций
```bash
# Откатить до предыдущей миграции
alembic downgrade -1

# Откатить до конкретной версии
alembic downgrade <revision_id>

# Откатить все миграции
alembic downgrade base
```

## Структура файлов

- `alembic.ini` - конфигурация Alembic
- `alembic/env.py` - настройки окружения для миграций
- `alembic/versions/` - папка с файлами миграций
- `alembic/script.py.mako` - шаблон для новых миграций

## Модели базы данных

Миграции созданы на основе моделей из `app/domain/auth_models.py`:

- `users` - таблица пользователей
- `user_identities` - таблица идентификаторов пользователей (OAuth, Telegram)
- `user_sessions` - таблица сессий пользователей

## Настройка подключения к базе данных

URL подключения к базе данных настраивается в `alembic.ini`:

```ini
sqlalchemy.url = postgresql://postgres:postgres@localhost:5432/layerbit
```

Для продакшена используйте переменные окружения или измените URL в конфигурации.
