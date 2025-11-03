# 📡 Примеры API запросов

Этот документ содержит примеры использования API Gateway Service.

## 🔑 Аутентификация

Все API запросы (кроме аутентификации) требуют API ключ в заголовке `X-API-Key`.

```bash
# Пример заголовка
curl -H "X-API-Key: your_secret_api_key_here" \
     http://localhost:8080/v1/insights/recommendations
```

## 👤 Аутентификация пользователей

### Регистрация с email/паролем

```bash
curl -X POST http://localhost:8080/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

**Ответ:**
```json
{
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "email_verified": false,
    "plan_type": "free",
    "trial_end_at": null,
    "telegram_account_id": null,
    "telegram_is_premium": null,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  },
  "tokens": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer",
    "expires_in": 900
  }
}
```

### Вход с email/паролем

```bash
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

### Аутентификация через Telegram

```bash
curl -X POST http://localhost:8080/auth/telegram \
  -H "Content-Type: application/json" \
  -d '{
    "id": 123456789,
    "first_name": "John",
    "last_name": "Doe",
    "username": "johndoe",
    "photo_url": "https://t.me/i/userpic/320/johndoe.jpg",
    "auth_date": 1640995200,
    "hash": "abc123def456..."
  }'
```

### Обновление токенов

```bash
curl -X POST http://localhost:8080/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }'
```

### Получение профиля пользователя

```bash
curl -X GET http://localhost:8080/auth/me \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

### Выход из системы

```bash
curl -X POST http://localhost:8080/auth/logout \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." \
  -d '{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }'
```

## 📊 Инсайты и рекомендации

### Получение рекомендаций

```bash
# Базовый запрос
curl -H "X-API-Key: your_secret_api_key_here" \
     "http://localhost:8080/v1/insights/recommendations"

# С фильтрами
curl -H "X-API-Key: your_secret_api_key_here" \
     "http://localhost:8080/v1/insights/recommendations?league=Premier%20League&from=2024-01-01T00:00:00Z&to=2024-01-31T23:59:59Z&min_conf=0.7&limit=20&offset=0"
```

**Параметры запроса:**
- `league` (опционально) - Фильтр по лиге
- `from` (опционально) - Начальная дата (ISO 8601)
- `to` (опционально) - Конечная дата (ISO 8601)
- `min_conf` (опционально) - Минимальная уверенность (0.0-1.0)
- `limit` (по умолчанию: 50) - Количество записей
- `offset` (по умолчанию: 0) - Смещение

**Ответ:**
```json
{
  "total": 150,
  "limit": 20,
  "offset": 0,
  "items": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "event_id": "456e7890-e89b-12d3-a456-426614174001",
      "league": "Premier League",
      "home_team": "Manchester United",
      "away_team": "Liverpool",
      "match_date": "2024-01-15T15:30:00Z",
      "prediction": "home_win",
      "confidence": 0.85,
      "odds": 2.1,
      "recommended_stake": 100.0,
      "expected_value": 0.15,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### Получение деталей события

```bash
curl -H "X-API-Key: your_secret_api_key_here" \
     "http://localhost:8080/v1/insights/events/456e7890-e89b-12d3-a456-426614174001"
```

**Ответ:**
```json
{
  "id": "456e7890-e89b-12d3-a456-426614174001",
  "league": "Premier League",
  "home_team": "Manchester United",
  "away_team": "Liverpool",
  "match_date": "2024-01-15T15:30:00Z",
  "status": "scheduled",
  "home_score": null,
  "away_score": null,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

## 📈 Статистика

### Получение сводной статистики

```bash
# Базовый запрос
curl -H "X-API-Key: your_secret_api_key_here" \
     "http://localhost:8080/v1/stats/summary"

# С фильтрами
curl -H "X-API-Key: your_secret_api_key_here" \
     "http://localhost:8080/v1/stats/summary?league=Premier%20League&from=2024-01-01T00:00:00Z&to=2024-01-31T23:59:59Z"
```

**Параметры запроса:**
- `league` (опционально) - Фильтр по лиге
- `from` (опционально) - Начальная дата (ISO 8601)
- `to` (опционально) - Конечная дата (ISO 8601)

**Ответ:**
```json
{
  "total_recommendations": 150,
  "successful_predictions": 120,
  "success_rate": 0.8,
  "total_events": 100,
  "completed_events": 95,
  "average_confidence": 0.75,
  "total_stake": 15000.0,
  "total_profit": 2500.0,
  "roi": 0.167,
  "period": {
    "from": "2024-01-01T00:00:00Z",
    "to": "2024-01-31T23:59:59Z"
  }
}
```

## 🔧 Системные эндпоинты

### Информация о сервисе

```bash
curl http://localhost:8080/
```

**Ответ:**
```json
{
  "service": "gateway-service",
  "version": "0.1.0",
  "status": "running",
  "environment": "development"
}
```

### Проверка здоровья

```bash
curl http://localhost:8080/health
```

**Ответ:**
```json
{
  "status": "healthy"
}
```

### Prometheus метрики

```bash
curl http://localhost:8080/metrics
```

**Ответ:**
```
# HELP http_requests_total Total number of HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/health",status="200"} 10
http_requests_total{method="GET",endpoint="/v1/insights/recommendations",status="200"} 5
...
```

## 🐍 Примеры на Python

### Базовый клиент

```python
import requests
import json

class GatewayClient:
    def __init__(self, base_url="http://localhost:8080", api_key=None):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({"X-API-Key": api_key})
    
    def get_recommendations(self, **params):
        response = self.session.get(
            f"{self.base_url}/v1/insights/recommendations",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def get_event_details(self, event_id):
        response = self.session.get(
            f"{self.base_url}/v1/insights/events/{event_id}"
        )
        response.raise_for_status()
        return response.json()
    
    def get_stats(self, **params):
        response = self.session.get(
            f"{self.base_url}/v1/stats/summary",
            params=params
        )
        response.raise_for_status()
        return response.json()

# Использование
client = GatewayClient(api_key="your_secret_api_key_here")

# Получение рекомендаций
recommendations = client.get_recommendations(
    league="Premier League",
    min_conf=0.7,
    limit=10
)

print(f"Найдено {recommendations['total']} рекомендаций")
for rec in recommendations['items']:
    print(f"{rec['home_team']} vs {rec['away_team']} - {rec['prediction']} (уверенность: {rec['confidence']})")
```

### Асинхронный клиент

```python
import aiohttp
import asyncio

class AsyncGatewayClient:
    def __init__(self, base_url="http://localhost:8080", api_key=None):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"X-API-Key": api_key} if api_key else {}
    
    async def get_recommendations(self, **params):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/v1/insights/recommendations",
                params=params,
                headers=self.headers
            ) as response:
                response.raise_for_status()
                return await response.json()

# Использование
async def main():
    client = AsyncGatewayClient(api_key="your_secret_api_key_here")
    
    recommendations = await client.get_recommendations(
        league="Premier League",
        min_conf=0.8
    )
    
    print(f"Найдено {recommendations['total']} рекомендаций")

# Запуск
asyncio.run(main())
```

## 🔒 Обработка ошибок

### Коды ошибок

- `400 Bad Request` - Неверные параметры запроса
- `401 Unauthorized` - Неверный API ключ или токен
- `403 Forbidden` - Доступ запрещен
- `404 Not Found` - Ресурс не найден
- `422 Unprocessable Entity` - Ошибка валидации данных
- `500 Internal Server Error` - Внутренняя ошибка сервера

### Пример обработки ошибок

```python
import requests
from requests.exceptions import HTTPError

try:
    response = requests.get(
        "http://localhost:8080/v1/insights/recommendations",
        headers={"X-API-Key": "invalid_key"}
    )
    response.raise_for_status()
    data = response.json()
except HTTPError as e:
    if e.response.status_code == 401:
        print("Ошибка аутентификации: неверный API ключ")
    elif e.response.status_code == 400:
        print("Ошибка запроса: неверные параметры")
    else:
        print(f"Ошибка сервера: {e.response.status_code}")
except requests.exceptions.RequestException as e:
    print(f"Ошибка сети: {e}")
```

## 📝 Примечания

1. **API ключи** должны быть переданы в заголовке `X-API-Key`
2. **JWT токены** должны быть переданы в заголовке `Authorization: Bearer <token>`
3. **Даты** должны быть в формате ISO 8601 (например: `2024-01-01T00:00:00Z`)
4. **Пагинация** поддерживается через параметры `limit` и `offset`
5. **Фильтрация** доступна для большинства эндпоинтов через query параметры
