# Frontend API Contract — Layerbit Oraculum AI

**Version**: MVP 1.0
**Base URL**: `$VITE_GATEWAY_BASE_URL` (например, `http://localhost:8001`)
**Формат**: JSON
**Аутентификация**: Bearer token в заголовке `Authorization: Bearer {access_token}`

---

## Общие принципы

### План-гейтинг (Free vs Pro)

- **Free**: только `soccer`, краткий reasoning, AI-Voting summary only, история за последние 3 дня
- **Pro**: все виды спорта (`soccer`, `basketball`, `tennis`, `hockey`), полный reasoning/context/voting, неограниченная история

### Visibility флаг

Некоторые эндпоинты возвращают `visibility` или `available` флаги, чтобы фронт мог скрывать/блокировать контент без жесткой ветвизации.

### Пагинация

Эндпоинты списков поддерживают:
- `limit` (опционально, default 20)
- `cursor` (опционально, для следующей страницы)
- Ответ содержит `next: string|null` для курсорной пагинации

### Ошибки

Все ошибки возвращаются в едином формате:

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": "any|optional"
  }
}
```

**Коды HTTP**:
- `400` — некорректный запрос
- `401` — требуется авторизация
- `403` — план не позволяет (например, Free пытается получить Pro-контент)
- `404` — ресурс не найден
- `429` — превышен лимит запросов
- `500` — внутренняя ошибка

---

## 1. Auth & Profile

### POST /v1/auth/email/register

Регистрация по email/паролю.

**Request**:
```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

**Response** (200):
```json
{
  "user": {
    "id": "string",
    "email": "string",
    "email_verified": false,
    "plan_type": "free",
    "created_at": "ISO8601"
  },
  "tokens": {
    "access_token": "string",
    "refresh_token": "string",
    "expires_in": 3600
  }
}
```

---

### POST /v1/auth/email/login

Вход по email/паролю.

**Request**:
```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

**Response** (200): аналогично `/register`.

---

### GET /v1/auth/me

Получить профиль текущего пользователя.

**Headers**: `Authorization: Bearer {access_token}`

**Response** (200):
```json
{
  "user": {
    "id": "string",
    "email": "string",
    "email_verified": true,
    "plan_type": "free|pro|partner",
    "created_at": "ISO8601"
  },
  "trial_left_days": 5,
  "is_trial_active": true
}
```

---

### POST /v1/auth/refresh

Обновить access token.

**Request**:
```json
{
  "refresh_token": "string"
}
```

**Response** (200):
```json
{
  "access_token": "string",
  "expires_in": 3600
}
```

---

### POST /v1/auth/logout

Logout (инвалидация refresh token).

**Request**:
```json
{
  "refresh_token": "string"
}
```

**Response** (204): No Content

---

## 2. Filters & Catalog

Публичные справочники для построения фильтров на фронте. План-гейтинг: в Free доступны только виды спорта/лиги, помеченные `available: true`.

### GET /v1/sports

Список видов спорта с учетом плана пользователя.

**Headers**: `Authorization: Bearer {access_token}` (опционально для анонимных — вернёт все виды с `available: false`)

**Response** (200):
```json
{
  "items": [
    {
      "code": "soccer",
      "title": "Soccer",
      "available": true
    },
    {
      "code": "basketball",
      "title": "Basketball",
      "available": false
    },
    {
      "code": "tennis",
      "title": "Tennis",
      "available": false
    },
    {
      "code": "hockey",
      "title": "Hockey",
      "available": false
    }
  ]
}
```

**Пример**:
```bash
curl "$VITE_GATEWAY_BASE_URL/v1/sports" \
  -H "Authorization: Bearer {token}"
```

---

### GET /v1/leagues

Список лиг для выбранного вида спорта.

**Query параметры**:
- `sport` (обязательно): `soccer|basketball|tennis|hockey`

**Response** (200):
```json
{
  "items": [
    {
      "code": "UEFA_CL",
      "title": "UEFA Champions League",
      "sport": "soccer"
    },
    {
      "code": "UEFA_EL",
      "title": "UEFA Europa League",
      "sport": "soccer"
    },
    {
      "code": "EPL",
      "title": "Premier League",
      "sport": "soccer"
    }
  ]
}
```

**Пример**:
```bash
curl "$VITE_GATEWAY_BASE_URL/v1/leagues?sport=soccer"
```

---

## 3. Events (Upcoming & Live)

Список и детали предстоящих/идущих событий. AI-Voting и Context вынесены в отдельные эндпоинты.

### GET /v1/events

Список событий с кратким reasoning и агрегированными коэффициентами.

**Query параметры**:
- `sport` (опционально): `soccer|basketball|tennis|hockey`
- `league` (опционально): код лиги
- `date` (опционально): `YYYY-MM-DD`
- `limit` (опционально): int, default 20
- `cursor` (опционально): string для пагинации

**Response** (200):
```json
{
  "items": [
    {
      "id": "evt-ucl-2025-10-21-bar-bay",
      "sport": "soccer",
      "league": "UEFA Champions League",
      "home": "Barcelona",
      "away": "Bayern Munich",
      "kickoff": "2025-10-21T19:00:00Z",
      "avgOdds": {
        "home": 2.3,
        "draw": 3.5,
        "away": 2.9
      },
      "bestOdds": {
        "home": 2.45,
        "draw": 3.65,
        "away": 3.05
      },
      "edgeScore": 6.2,
      "reasoningSummary": "Home form improving for Barcelona. Market slow to react.",
      "status": "upcoming"
    }
  ],
  "next": "cursor_string_or_null"
}
```

**Пример**:
```bash
curl "$VITE_GATEWAY_BASE_URL/v1/events?sport=soccer&league=UEFA%20Champions%20League&date=2025-10-21" \
  -H "Authorization: Bearer {token}"
```

---

### GET /v1/events/{id}

Базовая карточка события (без тяжёлого контекста и без AI-Voting breakdown).

**Response** (200):
```json
{
  "id": "evt-ucl-2025-10-21-bar-bay",
  "sport": "soccer",
  "league": "UEFA Champions League",
  "home": "Barcelona",
  "away": "Bayern Munich",
  "kickoff": "2025-10-21T19:00:00Z",
  "status": "upcoming",
  "oddsSeries": [
    {
      "t": "2025-10-21T10:00:00Z",
      "avg": { "home": 2.35, "draw": 3.45, "away": 2.95 },
      "best": { "home": 2.50, "draw": 3.60, "away": 3.10 }
    },
    {
      "t": "2025-10-21T18:00:00Z",
      "avg": { "home": 2.30, "draw": 3.50, "away": 2.90 },
      "best": { "home": 2.45, "draw": 3.65, "away": 3.05 }
    }
  ],
  "edgeScore": 6.2,
  "reasoningSummary": "Home form improving. Market slow to react.",
  "reasoningFull": "Detailed analysis available for Pro users...",
  "verdict": "confident"
}
```

**Plan-gейтинг**:
- Free: `reasoningFull` = краткая версия (первые 200 символов)
- Pro: полный текст

---

### GET /v1/events/{id}/context

Контекст события: lineups, injuries, weather, h2h.

**Response** (200):
```json
{
  "context": {
    "lineups": {
      "home": "4-3-3 formation with key attackers...",
      "away": "4-4-2 defensive setup..."
    },
    "injuries": {
      "home": [],
      "away": ["Midfielder out, affecting midfield creativity"]
    },
    "weather": "Clear, 15°C",
    "h2h": "Last 5 meetings: Barcelona 2 wins, Bayern 2 wins, 1 draw"
  },
  "visibility": "full"
}
```

**Plan-гейтинг**:
- Free: `visibility: "summary_only"`, некоторые поля могут быть `null` или усечены
- Pro: `visibility: "full"`, все поля доступны

**Пример**:
```bash
curl "$VITE_GATEWAY_BASE_URL/v1/events/evt-123/context" \
  -H "Authorization: Bearer {token}"
```

---

### GET /v1/events/{id}/voting

AI-Voting по событию: консенсус и (для Pro) расклад по моделям.

**Response** (200):
```json
{
  "aiConsensus": {
    "homePct": 48,
    "drawPct": 27,
    "awayPct": 25,
    "visibility": "full",
    "models": [
      {
        "name": "Model-A",
        "pick": "home",
        "confidence": 0.62,
        "note": "Strong home field advantage and recent form"
      },
      {
        "name": "Model-B",
        "pick": "draw",
        "confidence": 0.51,
        "note": "Conservative market pricing indicates tight match"
      }
    ]
  }
}
```

**Plan-гейтинг**:
- Free: `visibility: "summary_only"`, `models` = `[]`
- Pro: `visibility: "full"`, полный список моделей

**Пример**:
```bash
curl "$VITE_GATEWAY_BASE_URL/v1/events/evt-123/voting" \
  -H "Authorization: Bearer {token}"
```

---

## 4. History (Predicted vs Actual)

Выбор периода обязателен для серверной фильтрации. AI-Voting и Context по прошедшим событиям — отдельные запросы, формат идентичен предстоящим.

### GET /v1/history

Список прошедших событий с прогнозом и фактом.

**Query параметры**:
- `from` (обязательно): `YYYY-MM-DD`
- `to` (обязательно): `YYYY-MM-DD`
- `limit` (опционально): int, default 20
- `cursor` (опционально): string для пагинации

**Response** (200):
```json
{
  "items": [
    {
      "id": "hist-ucl-2025-10-14-psg-rma",
      "sport": "soccer",
      "league": "UEFA Champions League",
      "date": "2025-10-14",
      "teams": {
        "home": "PSG",
        "away": "Real Madrid"
      },
      "predicted": "home",
      "actual": "draw",
      "edgeAtPrediction": 5.1,
      "hit": false,
      "finalScore": "1-1"
    },
    {
      "id": "hist-uel-2025-10-13-ata-mun",
      "sport": "soccer",
      "league": "UEFA Europa League",
      "date": "2025-10-13",
      "teams": {
        "home": "Atalanta",
        "away": "Man United"
      },
      "predicted": "away",
      "actual": "away",
      "edgeAtPrediction": 4.3,
      "hit": true,
      "finalScore": "1-2"
    }
  ],
  "next": "cursor_string_or_null"
}
```

**Plan-гейтинг**:
- Free: `from`/`to` ограничены последними 3 днями от текущей даты
- Pro: любой период в пределах доступных данных

**Пример**:
```bash
curl "$VITE_GATEWAY_BASE_URL/v1/history?from=2025-10-01&to=2025-10-21" \
  -H "Authorization: Bearer {token}"
```

---

### GET /v1/history/{id}

Базовая деталь прошедшего события (видна фактическая развязка).

**Response** (200):
```json
{
  "id": "hist-ucl-2025-10-14-psg-rma",
  "sport": "soccer",
  "league": "UEFA Champions League",
  "teams": {
    "home": "PSG",
    "away": "Real Madrid"
  },
  "kickoff": "2025-10-14T19:00:00Z",
  "status": "finished",
  "finalScore": "1-1",
  "predicted": "home",
  "actual": "draw",
  "hit": false,
  "edgeAtPrediction": 5.1,
  "oddsSeries": [
    {
      "t": "2025-10-14T10:00:00Z",
      "avg": { "home": 2.1, "draw": 3.4, "away": 3.4 },
      "best": { "home": 2.2, "draw": 3.55, "away": 3.55 }
    },
    {
      "t": "2025-10-14T18:00:00Z",
      "avg": { "home": 2.05, "draw": 3.45, "away": 3.55 },
      "best": { "home": 2.15, "draw": 3.6, "away": 3.65 }
    }
  ],
  "reasoningFull": "AI models identified PSG's improved pressing...",
  "verdict": "risky"
}
```

---

### GET /v1/history/{id}/context

Контекст прошедшего события (тот же формат, что для `/events/{id}/context`).

**Response** (200):
```json
{
  "context": {
    "lineups": "PSG: 4-3-3, Real Madrid: 4-4-2",
    "injuries": {
      "home": [],
      "away": ["Midfielder out"]
    },
    "weather": "Clear, 15°C",
    "h2h": "Last 5 meetings: PSG 2 wins, Real Madrid 2 wins, 1 draw"
  },
  "visibility": "full"
}
```

---

### GET /v1/history/{id}/voting

AI-Voting по прошедшему событию (тот же формат, что `/events/{id}/voting`).

**Response** (200):
```json
{
  "aiConsensus": {
    "homePct": 48,
    "drawPct": 27,
    "awayPct": 25,
    "visibility": "full",
    "models": [
      {
        "name": "Model-A",
        "pick": "home",
        "confidence": 0.62,
        "note": "Strong home field advantage"
      }
    ]
  }
}
```

**Пример**:
```bash
curl "$VITE_GATEWAY_BASE_URL/v1/history/hist-456/voting" \
  -H "Authorization: Bearer {token}"
```

---

### GET /v1/history/summary

Итоги за период: accuracy, edge correlation, разрезы по лигам/видам спорта.

**Query параметры**:
- `from` (обязательно): `YYYY-MM-DD`
- `to` (обязательно): `YYYY-MM-DD`

**Response** (200):
```json
{
  "period": {
    "from": "2025-10-01",
    "to": "2025-10-21"
  },
  "metrics": {
    "total_predictions": 145,
    "hits": 98,
    "prediction_accuracy": 67.6,
    "avg_edge": 6.3,
    "edge_correlation": 0.72
  },
  "breakdown": {
    "byLeague": [
      {
        "league": "UEFA Champions League",
        "total": 24,
        "hits": 18,
        "accuracy": 75.0
      },
      {
        "league": "Premier League",
        "total": 38,
        "hits": 24,
        "accuracy": 63.2
      }
    ],
    "bySport": [
      {
        "sport": "soccer",
        "total": 120,
        "hits": 82,
        "accuracy": 68.3
      },
      {
        "sport": "basketball",
        "total": 25,
        "hits": 16,
        "accuracy": 64.0
      }
    ]
  }
}
```

**Plan-гейтинг**:
- Free: `from`/`to` ограничены последними 3 днями
- Pro: любой период

---

## 5. Pricing (Demo Mode)

### GET /v1/pricing/plans

Получить список доступных тарифов.

**Response** (200):
```json
{
  "plans": [
    {
      "code": "free",
      "title": "Free / Trial",
      "price": 0,
      "features": {
        "events_per_day": 20,
        "sports": ["soccer"],
        "reasoning": "summary_only",
        "history_days": 3
      }
    },
    {
      "code": "pro",
      "title": "Pro",
      "price": 20,
      "currency": "EUR",
      "features": {
        "events_per_day": 100,
        "sports": ["soccer", "basketball", "tennis", "hockey"],
        "reasoning": "full",
        "history_days": "unlimited"
      }
    }
  ]
}
```

---

## Примеры использования

### Получить список видов спорта
```bash
curl "$VITE_GATEWAY_BASE_URL/v1/sports" \
  -H "Authorization: Bearer {token}"
```

### Получить лиги для футбола
```bash
curl "$VITE_GATEWAY_BASE_URL/v1/leagues?sport=soccer"
```

### Получить события на конкретную дату
```bash
curl "$VITE_GATEWAY_BASE_URL/v1/events?sport=soccer&league=UEFA%20Champions%20League&date=2025-10-21" \
  -H "Authorization: Bearer {token}"
```

### Получить контекст события
```bash
curl "$VITE_GATEWAY_BASE_URL/v1/events/evt-123/context" \
  -H "Authorization: Bearer {token}"
```

### Получить AI-Voting для события
```bash
curl "$VITE_GATEWAY_BASE_URL/v1/events/evt-123/voting" \
  -H "Authorization: Bearer {token}"
```

### Получить историю за период
```bash
curl "$VITE_GATEWAY_BASE_URL/v1/history?from=2025-10-01&to=2025-10-21" \
  -H "Authorization: Bearer {token}"
```

### Получить AI-Voting для прошедшего события
```bash
curl "$VITE_GATEWAY_BASE_URL/v1/history/hist-456/voting" \
  -H "Authorization: Bearer {token}"
```

### Получить summary за период
```bash
curl "$VITE_GATEWAY_BASE_URL/v1/history/summary?from=2025-10-01&to=2025-10-21" \
  -H "Authorization: Bearer {token}"
```

---

## Rate Limits

- **Free**: 100 requests/hour
- **Pro**: 1000 requests/hour

При превышении лимита возвращается `429 Too Many Requests`:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "details": {
      "retry_after": 3600
    }
  }
}
```

---

## Заметки по интеграции

1. **Visibility флаги**: Проверяйте `visibility` и `available` поля для скрытия Pro-контента на Free плане
2. **План-гейтинг**: Free пользователи не могут запрашивать basketball/tennis/hockey — возвращается 403
3. **Пагинация**: Используйте `cursor` из ответа для загрузки следующей страницы
4. **Периоды истории**: Free ограничен последними 3 днями, запросы с большим периодом вернут 403
5. **Демо-режим**: Текущая версия не требует реальной оплаты, план меняется локально на фронте

---

**Документ актуален на**: 2025-10-21
**Контакт**: API Team @ Layerbit Oraculum AI
