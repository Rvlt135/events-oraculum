# Edge Agents Service - Project Structure and Architecture

## Overview
The Edge Agents Service is a FastAPI-based microservice designed for betting event analysis using AI agents. The service provides APIs for running analysis, generating recommendations, and managing internal operations related to betting events.

## Detailed Project Structure

### Root Directory
```
edge-agents-service/
├── app/                      # Main application package
├── boot/                     # Service bootstrapping
├── docs/                     # Documentation
├── prompts/                  # AI prompt templates
├── .env.example             # Example environment variables
├── .env.local.example       # Local development environment example
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile               # Docker configuration
└── requirements.txt         # Python dependencies
```

### App Directory
```
app/
├── cache/                   # Caching functionality
│   ├── __init__.py         # Cache package initialization
│   └── redis.py            # Redis cache implementation
│
├── config/                  # Configuration management
│   ├── __init__.py
│   ├── dependencies.py     # Dependency injection setup
│   ├── model_loader.py    # Model loading utilities
│   ├── models.yaml        # Model configurations
│   └── settings.py        # Application settings and environment variables
│
├── db/                      # Database layer
│   ├── __init__.py
│   ├── pg.py               # PostgreSQL connection and session management
│   └── repositories.py     # Database repositories and queries
│
├── models/                  # Database models
│   ├── __init__.py
│   └── recommendation.py   # Recommendation data models
│
├── routes/                  # API route handlers
│   ├── __init__.py
│   ├── health.py           # Health check endpoints
│   ├── internal.py         # Internal API endpoints
│   ├── recommendations.py  # Recommendation endpoints
│   └── run.py              # Agent execution endpoints
│
├── services/                # Business logic services
│   ├── agents/             # Agent implementations
│   │   ├── __init__.py
│   │   ├── base.py         # Base agent class
│   │   ├── llm_agent.py    # LLM-based agent implementation
│   │   └── persistence.py  # Agent persistence layer
│   │
│   ├── clients/            # External service clients
│   │   ├── __init__.py
│   │   ├── base.py         # Base client interface
│   │   ├── factory.py      # Client factory
│   │   ├── langchain_client.py  # LangChain client
│   │   ├── litellm_client.py    # LiteLLM client
│   │   └── openai_instructor.py # OpenAI Instructor client
│   │
│   ├── prompts/            # Prompt templates
│   │   └── ...             # Various prompt template files
│   │
│   ├── __init__.py
│   ├── features.py         # Feature engineering utilities
│   └── runner.py           # Agent execution runner
│
├── tasks/                   # Background tasks
│   ├── __init__.py
│   ├── broker.py          # Message broker setup
│   └── run_batch.py       # Batch processing tasks
│
├── __init__.py
└── main.py                # Application entry point
```

### Boot Directory
```
boot/
├── __init__.py
├── scheduler.py           # Task scheduler configuration
└── worker.py              # Background worker configuration
```

### Prompts Directory
```
prompts/
├── betting_analysis.yml    # Betting analysis prompt templates
├── conservative_analysis.yml  # Conservative analysis templates
└── value_hunting.yml       # Value hunting strategy templates
```

### Configuration Files

#### .env.example / .env.local.example
- Environment variable templates for different environments
- Database connection strings
- API keys and secrets
- Feature flags

#### docker-compose.yml
- Service definitions for:
  - Application service
  - PostgreSQL database
  - Redis cache
  - Monitoring stack (if applicable)

#### requirements.txt
- Python package dependencies
- Version-pinned for reproducibility

## Architecture Details

### Core Components

1. **API Layer**
   - FastAPI-based RESTful API
   - Async request handling
   - Automatic OpenAPI documentation
   - Request validation with Pydantic models

2. **Database Layer**
   - PostgreSQL for persistent storage
   - SQLAlchemy ORM with async support
   - Alembic for database migrations
   - Connection pooling for performance

3. **Caching Layer**
   - Redis for fast data access
   - Cache invalidation strategies
   - Distributed locking support

4. **Service Layer**
   - Modular service architecture
   - Dependency injection
   - Business logic encapsulation

5. **Agent System**
   - Pluggable agent architecture
   - Support for multiple LLM providers
   - Prompt templating system
   - Asynchronous execution

### Key Features

- **Modular Design**: Clear separation of concerns between components
- **Asynchronous Processing**: Non-blocking I/O operations
- **Containerization**: Docker support for easy deployment
- **Configuration Management**: Environment-based configuration
- **Structured Logging**: JSON-formatted logs with structlog
- **Caching**: Redis integration for performance optimization
- **Background Processing**: Task queue for long-running operations

## Development Setup

1. **Environment Setup**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Install Dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Run Services**
   ```bash
   # Start dependencies
   docker-compose up -d postgres redis
   
   # Run migrations (if any)
   # TODO: Add migration commands
   
   # Start the application
   uvicorn app.main:app --reload
   ```

4. **Access API Documentation**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Deployment

### Docker Compose
```bash
docker-compose up --build -d
```

### Environment Variables
Key environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `OPENAI_API_KEY`: OpenAI API key
- `ENVIRONMENT`: Runtime environment (development, staging, production)

## Monitoring and Logging

- Structured JSON logging with request IDs
- Error tracking integration
- Performance metrics
- Health check endpoints

## Testing

To be implemented:
- Unit tests with pytest
- Integration tests with testcontainers
- API tests with FastAPI TestClient
- Load testing with locust