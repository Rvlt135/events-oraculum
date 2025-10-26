# Odds Service - Old Structure Documentation

## Project Structure

```
odds-service/
├── .cursor/                 # Cursor IDE configuration
├── .dockerignore           # Docker ignore file
├── .env.example           # Example environment variables
├── .env.local.example     # Example local environment variables
├── .vscode/               # VS Code configuration
│   ├── launch.json
│   └── tasks.json
├── Dockerfile             # Docker configuration
├── README_CURSOR.md       # Cursor-specific README
├── README_OLD_STRUCTURE.md # This file
├── alembic/               # Database migrations
│   ├── versions/         # Migration scripts
│   ├── env.py            # Alembic environment
│   └── script.py.mako    # Migration script template
├── alembic.ini           # Alembic configuration
├── app/                  # Main application package
│   ├── __init__.py
│   ├── adapters/         # External service adapters
│   │   ├── dto/          # Data Transfer Objects
│   │   └── the_odds_api.py # The Odds API integration
│   ├── config/           # Configuration and dependencies
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   └── metrics.py
│   ├── domain/           # Business logic and models
│   │   ├── __init__.py
│   │   ├── base.py       # Base classes
│   │   ├── models.py     # Pydantic models
│   │   ├── orm_models.py # SQLAlchemy models
│   │   └── time_utils.py # Time-related utilities
│   ├── infra/            # Infrastructure layer
│   │   ├── repositories/ # Database repositories
│   │   ├── __init__.py
│   │   └── db.py         # Database configuration
│   ├── main.py           # FastAPI application entry point
│   ├── routes/           # API routes
│   ├── schemas/          # API schemas
│   └── tasks/            # Background tasks
│       └── collector.py  # Data collection tasks
├── boot/                 # Application startup scripts
│   ├── __init__.py
│   ├── scheduler.py      # Task scheduler
│   └── worker.py         # Worker process
├── db/                   # Database schema
│   └── schema.sql        # SQL schema definition
├── docs/                 # Documentation
│   ├── dbdiagram/        # Database diagrams
│   │   ├── ASSUMPTIONS.md
│   │   └── dbschema.dbml
│   ├── README_CURSOR.md
│   └── UNIFIED_APP_REFACTOR.md
├── requirements.txt      # Python dependencies
└── scripts/              # Utility scripts
```

## Key Components

### Application Structure
- **app/adapters**: Contains adapters for external services (e.g., The Odds API)
- **app/config**: Application configuration and dependency injection setup
- **app/domain**: Core business logic, models, and domain entities
- **app/infra**: Infrastructure components like database repositories
- **app/routes**: API route definitions
- **app/schemas**: Pydantic schemas for request/response validation
- **app/tasks**: Background tasks and scheduled jobs

### Database
- Uses SQLAlchemy ORM for database operations
- Alembic for database migrations
- Database schema defined in both SQL and ORM models

### Infrastructure
- FastAPI web framework
- Async database operations
- Background task processing
- Docker support

### Development
- VS Code configuration included
- Environment configuration examples provided
- Database schema documentation in DBML format

This structure follows a clean architecture approach with clear separation of concerns between different layers of the application.