# Odds Service Refactoring: Pydantic v2 + Timezone-Aware UTC + Centralized Sessions

This document describes the refactoring completed to modernize the odds-service codebase.

## Summary of Changes

### 1. Pydantic v2 Schemas

**Created:** `app/domain/schemas.py`

Introduced explicit Pydantic v2 schemas for all API contracts:

- **Enums:**
  - `Provider` - External API providers (e.g., THE_ODDS_API)
  - `Region` - Geographic regions (EU, US, UK, AU)
  - `Market` - Betting markets (H2H, SPREADS, TOTALS)
  - `SportType` - Sport categories
  - `EventStatus` - Event lifecycle states

- **Request/Response Models:**
  - `EventRef` - Event reference with UTC timestamps
  - `BookmakerOdds` - Bookmaker odds with metadata
  - `OddsItem` - Complete odds package for an event
  - `OddsQuery` - Query parameters for odds retrieval
  - `PaginationQuery` - Pagination parameters
  - `OddsResponse` - Paginated odds response
  - `SnapshotSummary` - Normalized odds snapshot
  - `SnapshotsResponse` - Collection of snapshots
  - `TaskTriggerResponse` - Async task trigger result
  - `HealthResponse` - Health check response
  - `ServiceInfoResponse` - Service metadata

**Features:**
- All datetime fields serialize to ISO-8601 format with 'Z' suffix (UTC)
- `ConfigDict(from_attributes=True)` for ORM compatibility
- Field serializers ensure timezone-aware datetime handling
- Type-safe enums for all categorical data

### 2. Timezone-Aware UTC Handling

**Created:** `app/domain/time_utils.py`

Replaced deprecated `datetime.utcnow()` throughout the codebase:

**Functions:**
- `now_utc()` - Returns current UTC time (timezone-aware)
- `ensure_utc(dt)` - Converts any datetime to UTC-aware
- `parse_utc(dt_str)` - Parses ISO-8601 strings to UTC

**Files Updated:**
- `app/domain/models.py` - Replaced default_factory
- `app/domain/orm_models.py` - Updated column defaults
- `app/infra/repositories/event.py` - Update timestamp handling
- `app/infra/repositories/team.py` - Update timestamp handling
- `app/infra/repositories/odds_snapshot.py` - Ingestion timestamps
- `app/infra/repositories/normalized_odds.py` - Normalization timestamps
- `app/tasks/collector.py` - Collection task timestamps
- `app/tasks/normalizer.py` - Event processing timestamps

**Impact:**
- All timestamps are now timezone-aware (UTC)
- No more naive datetime objects in the system
- Consistent serialization across all APIs

### 3. Centralized Session Management

**Enhanced:** `app/infra/db.py`

- Added `autoflush=False` to session factory for explicit control
- Session lifecycle managed through DI (Dependency Injection)
- `get_db_session()` dependency provides async context management

**Created:** `app/infra/unit_of_work.py`

Implemented Unit of Work pattern for transaction management:

```python
async with UnitOfWork(session) as uow:
    await repository.create(entity)
    await uow.commit()
```

**Features:**
- Explicit transaction boundaries
- Automatic rollback on exceptions
- Optional manual commit/rollback
- Debug logging for transaction lifecycle

### 4. API Modernization

**Updated:** `app/admin_api/app.py`

- All endpoints now use Pydantic v2 response models
- Added `ORJSONResponse` as default for performance
- Type-safe request/response contracts
- Proper error handling with schema validation

**Endpoints:**
- `GET /` - Service info (ServiceInfoResponse)
- `GET /health` - Health check (HealthResponse)
- `POST /_admin/tasks/collect` - Trigger collection (TaskTriggerResponse)
- `GET /_admin/data/snapshots` - Get snapshots (SnapshotsResponse)
- `GET /metrics` - Prometheus metrics

## Architecture Benefits

### Type Safety
- Full type hints throughout the codebase
- Pydantic validation at API boundaries
- No ORM models exposed in responses

### Maintainability
- Clear separation: Domain models vs. API schemas
- Centralized time handling (single source of truth)
- Explicit transaction boundaries

### Performance
- ORJSON for fast JSON serialization
- Connection pooling with proper lifecycle management
- No N+1 session creation issues

### Reliability
- Timezone-aware timestamps prevent subtle bugs
- Unit of Work ensures transactional consistency
- DI pattern enables easier testing

## Migration Notes

### Before
```python
# Old pattern - DEPRECATED
created_at = datetime.utcnow()  # Naive datetime
session = AsyncSession(...)     # Manual session creation
```

### After

```python
# New pattern
from app.domain.utils.time_utils import now_utc
from app.infra.unit_of_work import UnitOfWork

created_at = now_utc()  # Timezone-aware UTC


# Sessions via DI
async def handler(session: AsyncSession = Depends(get_db_session)):
    async with UnitOfWork(session) as uow:
        await repository.save(entity)
        await uow.commit()
```

## Testing Recommendations

### Unit Tests
- Test Pydantic validators (datetime parsing, enums)
- Test UnitOfWork commit/rollback behavior
- Test time_utils functions with various inputs

### Integration Tests
- Verify API responses match schemas
- Test transaction boundaries with failures
- Verify UTC serialization in responses

### Performance Tests
- Benchmark ORJSON vs standard JSON
- Verify no session leaks under load
- Check connection pool behavior

## Future Improvements

1. **Add Response Models** to remaining services (edge-agents, gateway)
2. **Implement Alembic** migrations for schema versioning
3. **Add OpenAPI tags** for better API documentation
4. **Add Request ID** tracing for distributed debugging
5. **Implement Circuit Breaker** for external API calls

## Acceptance Criteria - Verified

- ✅ All public endpoints use Pydantic v2 models
- ✅ No `datetime.utcnow()` calls in codebase
- ✅ All datetime fields are timezone-aware (UTC)
- ✅ Serialization produces ISO-8601 with 'Z' suffix
- ✅ No direct `AsyncSession()` constructors in code
- ✅ Sessions managed via DI (`get_db_session()`)
- ✅ Transactions use UnitOfWork pattern
- ✅ Build succeeds without errors
- ✅ Type hints preserved throughout

## Dependencies

No new dependencies added. Existing dependencies used:
- `pydantic>=2.9.0` (already present)
- `orjson>=3.10.0` (already present)
- `SQLAlchemy[asyncio]>=2.0.0` (already present)

## Breaking Changes

None. All changes are internal refactoring. External API contracts remain compatible.
