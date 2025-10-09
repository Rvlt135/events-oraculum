# Docker Compose Architecture

This project uses a split Docker Compose architecture for flexible deployment:

- **Infrastructure only** (Redis, PostgreSQL)
- **Service-specific** compose files (odds, agents, gateway)
- **Local development** support with containerized infrastructure

## Quick Start

### 1. Start Infrastructure

First, start the core infrastructure (Redis + PostgreSQL):

```bash
docker compose -f infrastructure/docker-compose.infra.yml up -d
```

This creates the `layerbit-net` network and starts:
- PostgreSQL on `localhost:5432`
- Redis on `localhost:6379`

### 2. Choose Your Deployment Strategy

#### Option A: Run Services in Docker

Start specific services as needed:

```bash
# Odds service (admin API + worker + scheduler)
docker compose -f infrastructure/docker-compose.odds.yml up -d

# Edge agents service (API + worker + scheduler)
docker compose -f infrastructure/docker-compose.agents.yml up -d

# Gateway service
docker compose -f infrastructure/docker-compose.gateway.yml up -d
```

#### Option B: Run Services Locally (Host Process)

For development, run services as local Python processes while using Docker infrastructure.

**Prerequisites:**
1. Infrastructure must be running (see step 1)
2. Create `.env` file from `.env.example` in each service directory
3. Update connection settings for localhost access

**Local Environment Configuration:**

For each service, copy `.env.example` to `.env` and update:

```env
# Change from container names to localhost
REDIS_URL=redis://localhost:6379/0
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=layerbit
```

**Run Services:**

```bash
# Odds Service - Admin API
cd odds-service
python -m boot.admin_api

# Odds Service - Worker
cd odds-service
python -m boot.worker

# Odds Service - Scheduler
cd odds-service
python -m boot.scheduler

# Edge Agents - API
cd edge-agents-service
uvicorn app.main:app --host 0.0.0.0 --port 8082

# Edge Agents - Worker
cd edge-agents-service
python -m boot.worker

# Edge Agents - Scheduler
cd edge-agents-service
python -m boot.scheduler

# Gateway Service
cd gateway-service
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## Service Endpoints

When running (either in Docker or locally):

- **Odds Admin API**: http://localhost:8081
- **Edge Agents API**: http://localhost:8082
- **Gateway API**: http://localhost:8080
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## Management Commands

### Infrastructure

```bash
# Start infrastructure
docker compose -f infrastructure/docker-compose.infra.yml up -d

# Stop infrastructure (keeps data)
docker compose -f infrastructure/docker-compose.infra.yml stop

# Stop and remove infrastructure (keeps volumes)
docker compose -f infrastructure/docker-compose.infra.yml down

# Stop and remove everything including data
docker compose -f infrastructure/docker-compose.infra.yml down -v

# View logs
docker compose -f infrastructure/docker-compose.infra.yml logs -f

# Check status
docker compose -f infrastructure/docker-compose.infra.yml ps
```

### Individual Services

```bash
# Odds Service
docker compose -f infrastructure/docker-compose.odds.yml up -d
docker compose -f infrastructure/docker-compose.odds.yml down
docker compose -f infrastructure/docker-compose.odds.yml logs -f

# Agents Service
docker compose -f infrastructure/docker-compose.agents.yml up -d
docker compose -f infrastructure/docker-compose.agents.yml down
docker compose -f infrastructure/docker-compose.agents.yml logs -f

# Gateway Service
docker compose -f infrastructure/docker-compose.gateway.yml up -d
docker compose -f infrastructure/docker-compose.gateway.yml down
docker compose -f infrastructure/docker-compose.gateway.yml logs -f
```

## Make-Style Commands

You can add these aliases to your shell profile for convenience:

```bash
# Infrastructure
alias infra-up='docker compose -f infrastructure/docker-compose.infra.yml up -d'
alias infra-down='docker compose -f infrastructure/docker-compose.infra.yml down'
alias infra-logs='docker compose -f infrastructure/docker-compose.infra.yml logs -f'
alias infra-ps='docker compose -f infrastructure/docker-compose.infra.yml ps'

# Odds Service
alias odds-up='docker compose -f infrastructure/docker-compose.odds.yml up -d'
alias odds-down='docker compose -f infrastructure/docker-compose.odds.yml down'
alias odds-logs='docker compose -f infrastructure/docker-compose.odds.yml logs -f'

# Agents Service
alias agents-up='docker compose -f infrastructure/docker-compose.agents.yml up -d'
alias agents-down='docker compose -f infrastructure/docker-compose.agents.yml down'
alias agents-logs='docker compose -f infrastructure/docker-compose.agents.yml logs -f'

# Gateway Service
alias gateway-up='docker compose -f infrastructure/docker-compose.gateway.yml up -d'
alias gateway-down='docker compose -f infrastructure/docker-compose.gateway.yml down'
alias gateway-logs='docker compose -f infrastructure/docker-compose.gateway.yml logs -f'

# Combined
alias all-up='infra-up && odds-up && agents-up && gateway-up'
alias all-down='gateway-down && agents-down && odds-down && infra-down'
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                   │
│  (docker-compose.infra.yml)                             │
│                                                          │
│  ┌──────────────┐              ┌──────────────┐        │
│  │  PostgreSQL  │              │    Redis     │        │
│  │  :5432       │              │    :6379     │        │
│  └──────────────┘              └──────────────┘        │
│         ▲                              ▲                │
└─────────┼──────────────────────────────┼────────────────┘
          │                              │
    ┌─────┴──────────────────────────────┴─────┐
    │         layerbit-net network              │
    └─────┬──────────────┬──────────────┬───────┘
          │              │              │
┌─────────▼────────┐ ┌──▼─────────┐ ┌──▼──────────┐
│  Odds Service    │ │  Agents    │ │  Gateway    │
│  (.odds.yml)     │ │ (.agents)  │ │ (.gateway)  │
│                  │ │            │ │             │
│ • Admin API      │ │ • API      │ │ • API       │
│ • Worker         │ │ • Worker   │ │             │
│ • Scheduler      │ │ • Scheduler│ │             │
│ :8081            │ │ :8082      │ │ :8080       │
└──────────────────┘ └────────────┘ └─────────────┘
```

## Dependency Order

1. **First**: Start infrastructure (required)
2. **Then**: Start any combination of services

Services cannot start without infrastructure, but are otherwise independent.

## Development Workflow Examples

### Full Docker Deployment

```bash
# Start everything
docker compose -f infrastructure/docker-compose.infra.yml up -d
docker compose -f infrastructure/docker-compose.odds.yml up -d
docker compose -f infrastructure/docker-compose.agents.yml up -d
docker compose -f infrastructure/docker-compose.gateway.yml up -d

# Stop everything
docker compose -f infrastructure/docker-compose.gateway.yml down
docker compose -f infrastructure/docker-compose.agents.yml down
docker compose -f infrastructure/docker-compose.odds.yml down
docker compose -f infrastructure/docker-compose.infra.yml down
```

### Hybrid: Infra in Docker, Services Local

```bash
# Start infrastructure only
docker compose -f infrastructure/docker-compose.infra.yml up -d

# Run services locally (see "Run Services Locally" section above)
cd gateway-service
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# In another terminal
cd edge-agents-service
python -m boot.worker
```

### Single Service Development

```bash
# Infrastructure + only the service you're working on
docker compose -f infrastructure/docker-compose.infra.yml up -d
docker compose -f infrastructure/docker-compose.odds.yml up -d

# Or run that service locally for faster iteration
cd odds-service
python -m boot.admin_api
```

## Troubleshooting

### Network Issues

If services can't find infrastructure:

```bash
# Ensure network exists
docker network ls | grep layerbit-net

# Recreate if needed
docker network create layerbit-net
```

### Connection Refused (Local to Docker)

Ensure ports are published in `docker-compose.infra.yml`:
- PostgreSQL: `5432:5432`
- Redis: `6379:6379`

### Service Can't Connect to Database

1. Check infrastructure is running: `docker compose -f infrastructure/docker-compose.infra.yml ps`
2. Verify connection settings in service `.env`
3. For Docker services: use `postgres` and `redis` as hostnames
4. For local services: use `localhost`

### Data Persistence

Volumes are preserved between `down` and `up`. To completely reset:

```bash
docker compose -f infrastructure/docker-compose.infra.yml down -v
```

**Warning**: This deletes all data!

## Notes

- The original `docker-compose.yml` has been superseded by these split files
- No single "run everything" compose file exists by design
- Each service is independently scalable
- Infrastructure network is external to all service compose files
