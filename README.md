# Layerbit-Oraculum-AI Backend MVP

AI-powered betting analysis system for sports events. This MVP focuses on UEFA Champions League football events with a modular, extensible architecture.

## Architecture

Monorepo structure with three microservices:

1. **odds-service** - Data collection, normalization, and storage
2. **gateway-service** - Public API for insights and recommendations (pending)
3. **edge-agents-service** - AI agents for analysis and predictions (pending)

## Project Structure

```
layerbit-oraculum-ai/
├── shared/                     # Shared models and configuration
│   ├── config.py              # Application configuration
│   └── models.py              # Domain models
├── services/
│   └── odds_service/          # Odds collection service
│       ├── api/               # FastAPI application
│       │   ├── app.py
│       │   └── routes/        # API endpoints
│       ├── clients/           # External API clients
│       │   └── odds_api.py    # The Odds API integration
│       ├── repositories/      # Database layer
│       │   ├── base.py
│       │   └── events_repository.py
│       ├── services/          # Business logic
│       │   └── normalizer.py  # Data normalization
│       ├── tasks/             # Background tasks
│       │   └── scheduler.py   # TaskIQ scheduler
│       ├── config.py          # Service configuration
│       ├── main.py            # API server entry point
│       └── scheduler_main.py  # Scheduler entry point
├── migrations/                # SQL migrations
│   └── 001_create_odds_service_schema.sql
├── pyproject.toml             # Python dependencies
└── package.json               # Build scripts

```

## Current Status: Phase 1 - odds-service

The odds-service implements:
- Data collection from The Odds API
- Team name normalization
- Odds aggregation and statistics
- Scheduled collection (every 12 hours)
- Admin API for manual triggers

## Database Schema

Tables:
- `sports` - Sports reference data
- `leagues` - Leagues/competitions
- `teams` - Teams with normalized names
- `events` - Betting events (matches)
- `bookmakers` - Bookmaker reference data
- `odds_snapshots` - Raw odds data from API
- `normalized_odds` - Aggregated odds statistics

## Setup

### Prerequisites
- Python 3.12+
- PostgreSQL (via Supabase)
- Redis

### Installation

1. Install dependencies:
```bash
pip install -e .
```

2. Configure environment:
```bash
# Update .env with your credentials
ODDS_API_KEY=your_key_here
```

3. Apply database migration:
```bash
# Run the SQL migration in migrations/001_create_odds_service_schema.sql
# through Supabase SQL Editor or psql
```

### Running odds-service

Start the API server:
```bash
python -m services.odds_service.main
```

Start the scheduler:
```bash
python -m services.odds_service.scheduler_main
```

### API Endpoints

Health checks:
- `GET /health` - Service health
- `GET /health/odds-api` - External API connectivity

Events:
- `GET /api/v1/events/upcoming` - List upcoming events

Admin:
- `POST /api/v1/admin/trigger-collection` - Trigger manual collection
- `GET /api/v1/admin/stats` - Service statistics

## Next Steps

After approval of odds-service:
1. Implement gateway-service (public API)
2. Implement edge-agents-service (AI analysis)

## Technology Stack

- FastAPI - Web framework
- TaskIQ - Task scheduler
- PostgreSQL - Persistent storage
- Redis - Caching and task queue
- HTTPX - Async HTTP client
- Pydantic v2 - Data validation