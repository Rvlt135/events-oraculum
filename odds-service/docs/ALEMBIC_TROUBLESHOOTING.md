# Решение проблем с Alembic миграциями

## Проблема: Multiple head revisions

**Ошибка:**
```
ERROR: Multiple head revisions are present for given argument 'head'
```

**Причина:** В проекте есть несколько веток миграций, которые не объединены в одну цепочку.

## Решение (пошагово):

### 1. Проверить текущие head ревизии
```bash
alembic heads
```
Вы увидите список всех head ревизий, например:
```
39a6a5bedbcc (head)
e6_events_idempotency (head)
```

### 2. Проверить текущее состояние БД
```bash
alembic current
```
Это покажет, какая миграция применена в БД.

### 3. Создать merge-миграцию
```bash
alembic merge -m "merge_description" <revision1> <revision2>
```
Например:
```bash
alembic merge -m "merge_all_heads" 39a6a5bedbcc e6_events_idempotency
```

### 4. Применить миграции
```bash
alembic upgrade head
```

### 5. Проверить результат
```bash
alembic heads
```
Должен быть только один head:
```
7dceed314198 (head)
```

## Как избежать проблемы в будущем:

1. **Всегда проверяйте heads перед созданием новой миграции:**
   ```bash
   alembic heads
   ```

2. **Если есть несколько heads, создайте merge перед новой миграцией:**
   ```bash
   alembic merge -m "merge_branches" <head1> <head2>
   alembic upgrade head
   ```

3. **При создании новой миграции указывайте конкретный head:**
   ```bash
   alembic revision --head=<revision_id> -m "description"
   ```

4. **Или используйте autogenerate только когда есть один head:**
   ```bash
   alembic revision --autogenerate -m "description"
   ```

## Полезные команды:

- `alembic heads` - показать все head ревизии
- `alembic current` - показать текущую примененную миграцию
- `alembic history` - показать историю миграций
- `alembic show <revision>` - показать детали миграции
- `alembic upgrade head` - применить все миграции до head
- `alembic downgrade -1` - откатить последнюю миграцию

