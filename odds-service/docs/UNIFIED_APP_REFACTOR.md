# Odds Service Unified Application Refactoring

This document describes the refactoring that consolidates the odds-service into a single FastAPI application with both public and admin functionality.

## Overview

Previously, the odds-service ran as multiple processes:
- Public API (port 8083)
- Admin API (port 8081)
- Worker process
- Scheduler process

Now, it runs as:
- **Single unified FastAPI app** (port 8083) with public and admin routes
- Worker process (shares infrastructure)
- Scheduler process (shares infrastructure)

## Key Changes

### 1. Unified Infrastructure Provider

**Created:** `app/infra/providers.py`

Centralized singleton for all infrastructure resources:
- Database (AsyncEngine, session factory)
- Redis client
- TaskIQ broker
- Configuration

**Benefits:**
- No duplicate initialization
- Shared across main app, scheduler, and worker
- Clean lifecycle management

**Usage:**
```python
from app.infra.providers import infrastructure, get_db_session

# In FastAPI routes
async def handler(session: AsyncSession = Depends(get_db_session)):
    ...

# In boot scripts
await infrastructure.initialize()
# ... use infrastructure.session_factory()
await infrastructure.dispose()
```

### 2. Single FastAPI Application

**Updated:** `app/main.py`

The main application now includes:
- Public routes (root mounted)
- Admin routes (mounted under `/_admin`)
- Shared metrics endpoint
- Conditional admin mounting based on configuration

**Features:**
- ORJSON for fast serialization
- Metrics middleware tracking public vs admin requests
- Unified lifespan management
- CORS middleware

### 3. Admin Routes

**Created:** `app/routes/admin.py`

Admin endpoints moved to dedicated router:
- `POST /_admin/tasks/collect` - Trigger collection task
- `GET /_admin/data/snapshots` - View normalized odds

**Security:**
- Optional token authentication via `X-Admin-Token` header
- Can be completely disabled via `ADMIN_ENABLED=false`
- Docs can be hidden via `ADMIN_DOCS_ENABLED=false`

### 4. Public Routes

**Created:** `app/routes/public.py`

Public endpoints:
- `GET /` - Service info
- `GET /health` - Health check
- `GET /liveness` - K8s liveness probe
- `GET /readiness` - K8s readiness probe

### 5. Updated Boot Scripts

**Updated:**
- `boot/scheduler.py` - Uses shared infrastructure
- `boot/worker.py` - Uses shared infrastructure

**Removed:**
- `boot/admin_api.py` - No longer needed
- `app/admin_api/` - Functionality merged into main app

### 6. Configuration Changes

**Updated:** `app/config/settings.py`

New settings:
```python
API_HOST = "0.0.0.0"
API_PORT = 8083
ADMIN_ENABLED = true
ADMIN_PREFIX = "/_admin"
ADMIN_TOKEN = ""  # Optional token for admin auth
ADMIN_DOCS_ENABLED = false  # Include admin in OpenAPI schema
```

**Removed:**
```python
ADMIN_API_HOST  # No longer needed
ADMIN_API_PORT  # No longer needed
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Unified FastAPI Application                 │
│                    (Port 8083)                          │
│                                                          │
│  ┌──────────────────┐  ┌─────────────────────────┐     │
│  │  Public Routes   │  │   Admin Routes          │     │
│  │  /               │  │   /_admin/tasks/collect │     │
│  │  /health         │  │   /_admin/data/...      │     │
│  │  /liveness       │  │   (protected)           │     │
│  │  /readiness      │  │                         │     │
│  └──────────────────┘  └─────────────────────────┘     │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │          Shared Infrastructure                  │    │
│  │  - Database (AsyncEngine, SessionFactory)      │    │
│  │  - Redis Client                                 │    │
│  │  - Metrics                                      │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
              │                              │
              │                              │
    ┌─────────▼────────┐          ┌─────────▼────────┐
    │  Worker Process   │          │ Scheduler Process │
    │  (boot.worker)    │          │ (boot.scheduler)  │
    │                   │          │                   │
    │  Uses shared      │          │  Uses shared      │
    │  infrastructure   │          │  infrastructure   │
    └───────────────────┘          └───────────────────┘
```

## Deployment

### Single Process (Main App)

```bash
# Start unified application
python -m app.main

# Or via uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8083
```

### With Worker and Scheduler

```bash
# Terminal 1: Main app
python -m app.main

# Terminal 2: Worker
python -m boot.worker

# Terminal 3: Scheduler
python -m boot.scheduler
```

### Docker Compose

```yaml
services:
  odds-api:
    command: python -m app.main
    ports:
      - "8083:8083"
    environment:
      - ADMIN_ENABLED=true
      - ADMIN_TOKEN=secret_token_here

  odds-worker:
    command: python -m boot.worker

  odds-scheduler:
    command: python -m boot.scheduler
```

## Configuration Examples

### Public Only (No Admin)

```env
API_PORT=8083
ADMIN_ENABLED=false
```

### Admin Enabled (No Token)

```env
API_PORT=8083
ADMIN_ENABLED=true
ADMIN_PREFIX=/_admin
ADMIN_TOKEN=
```

**Note:** Secure at network level (ingress, reverse proxy, IP allowlist)

### Admin with Token

```env
API_PORT=8083
ADMIN_ENABLED=true
ADMIN_PREFIX=/_admin
ADMIN_TOKEN=your-secret-token-here
ADMIN_DOCS_ENABLED=false
```

**Usage:**
```bash
curl -H "X-Admin-Token: your-secret-token-here" \
  http://localhost:8083/_admin/tasks/collect
```

### Admin in OpenAPI Docs

```env
ADMIN_ENABLED=true
ADMIN_DOCS_ENABLED=true
```

Visit `http://localhost:8083/docs` to see admin endpoints.

## Security Recommendations

### Development
- Use `ADMIN_TOKEN` for basic protection
- Enable `ADMIN_DOCS_ENABLED=true` for testing

### Staging
- Set `ADMIN_TOKEN` to strong random value
- Disable docs: `ADMIN_DOCS_ENABLED=false`
- Consider IP allowlist at ingress

### Production
- **Network-level security (required)**:
  - Ingress allowlist (admin IPs only)
  - mTLS for admin routes
  - VPN or bastion host
  - Service mesh policies

- **Application-level (defense in depth)**:
  - Strong `ADMIN_TOKEN`
  - Rate limiting
  - Audit logging

- **Option: Disable entirely**:
  ```env
  ADMIN_ENABLED=false
  ```
  Deploy separate admin pod if needed

## Metrics

All HTTP requests tracked by route type:

```prometheus
# Public requests
odds_service_http_requests_total{method="GET",path="/health",route_type="public"}

# Admin requests
odds_service_http_requests_total{method="POST",path="/_admin/tasks/collect",route_type="admin"}
```

## Migration Guide

### From Old Deployment

**Before:**
```yaml
services:
  odds-api:
    command: python -m app.main
    ports:
      - "8083:8083"

  odds-admin-api:
    command: python -m boot.admin_api
    ports:
      - "8081:8081"

  odds-worker:
    command: python -m boot.worker

  odds-scheduler:
    command: python -m boot.scheduler
```

**After:**
```yaml
services:
  odds-api:
    command: python -m app.main
    ports:
      - "8083:8083"  # Handles both public and admin
    environment:
      - ADMIN_ENABLED=true

  odds-worker:
    command: python -m boot.worker

  odds-scheduler:
    command: python -m boot.scheduler
```

### Update Service Calls

**Before:**
```bash
# Admin endpoint
curl http://odds-admin-api:8081/tasks/collect
```

**After:**
```bash
# Admin endpoint (with token)
curl -H "X-Admin-Token: token" http://odds-api:8083/_admin/tasks/collect
```

## Testing

### Smoke Tests

```bash
# Public endpoints
curl http://localhost:8083/
curl http://localhost:8083/health
curl http://localhost:8083/liveness
curl http://localhost:8083/readiness

# Admin endpoints (if ADMIN_TOKEN set)
curl -H "X-Admin-Token: your-token" http://localhost:8083/_admin/tasks/collect
curl -H "X-Admin-Token: your-token" http://localhost:8083/_admin/data/snapshots

# Metrics
curl http://localhost:8083/metrics
```

### Integration Tests

1. Start infrastructure: `docker compose -f infrastructure/docker-compose.infra.yml up -d`
2. Start app: `python -m app.main`
3. Start worker: `python -m boot.worker`
4. Start scheduler: `python -m boot.scheduler`
5. Trigger collection: `curl -X POST -H "X-Admin-Token: token" http://localhost:8083/_admin/tasks/collect`
6. Check snapshots: `curl -H "X-Admin-Token: token" http://localhost:8083/_admin/data/snapshots?limit=10`

## Benefits

1. **Simplified Deployment**: One main process instead of two
2. **Reduced Resource Usage**: Shared infrastructure, no duplicate connections
3. **Easier Development**: Single entrypoint for development
4. **Better Metrics**: Unified metrics with route type labels
5. **Flexible Security**: Can disable admin, add token, or secure at network level
6. **Maintainability**: Single codebase, clearer architecture

## Breaking Changes

- Admin API no longer runs on separate port
- Admin endpoints moved to `/_admin` prefix
- Environment variables changed:
  - `ADMIN_API_HOST` → `API_HOST`
  - `ADMIN_API_PORT` → `API_PORT`
- New variables: `ADMIN_ENABLED`, `ADMIN_PREFIX`, `ADMIN_TOKEN`

## Backward Compatibility

The `app/infra/db.py` module is kept for backward compatibility but deprecated. All imports should use `app.infra.providers` instead.

## Future Enhancements

1. **RBAC**: Role-based access control for admin endpoints
2. **JWT Auth**: Replace simple token with JWT
3. **Audit Log**: Track all admin operations
4. **Rate Limiting**: Per-route rate limits
5. **WebSocket Admin**: Real-time monitoring dashboard
6. **Admin UI**: Web interface for admin operations
