# Current Agents Logic Overview

## 1. Existing Services

### RecommendationService
- Located in `app/services/recommendation/service.py`
- Manages recommendation persistence and caching
- Dependencies: `async_sessionmaker[AsyncSession]`, `RecommendationCache`
- Methods:
  - `save_recommendation()`: Persists to DB and caches in Redis
  - `get_recommendations()`: Queries DB with filters (league, date range, confidence)
  - `get_recommendations_by_event()`: Legacy method for event-specific queries
  - `get_from_cache_or_db()`: Cache-first retrieval with DB fallback

### FeatureService
- Located in `app/services/features.py`
- Extracts event features from database
- Dependencies: `async_sessionmaker[AsyncSession]`
- Methods:
  - `get_event_features()`: SQL query for event data (teams, odds, league info)

### FeatureBuilder
- Located in `app/services/features.py`
- Alternative feature extraction using asyncpg pool
- Dependencies: `postgres_url` string
- Methods:
  - `get_event_features()`: Direct asyncpg query
  - `get_events_by_league()`: Filters events by league and date range
  - `connect()` / `disconnect()`: Pool lifecycle management

## 2. Existing Agents

### Agent (Base Class)
- Located in `app/services/agents/base.py`
- Abstract base class defining agent interface
- Methods:
  - `analyze()`: Abstract method returning `Optional[AgentPrediction]`
  - `get_model_version()`: Abstract method returning version string

### LLMAgent
- Located in `app/services/agents/llm_agent.py`
- Single concrete agent implementation
- Initialization: Requires `BaseLLMClient` and `prompt_template` string
- Dependencies: `BaseLLMClient`, `PromptProcessor`, `RecommendationSchema`
- Methods:
  - `analyze()`: Processes event features → generates prompt → calls LLM → returns `AgentPrediction`
  - `get_model_version()`: Returns composite version string (model_id + template + v2)
- Flow: Features → PromptProcessor → LLM Client → Structured output → AgentPrediction

## 3. Existing Pipelines

### AgentRunner
- Located in `app/services/runner.py`
- Sequential batch processing pipeline
- Initialization: Requires `RecommendationRepository`, optional `prompt_template` and `model_name`
- Dependencies: `FeatureBuilder`, `LLMAgent`, `RecommendationRepository`
- Methods:
  - `run_batch()`: Processes events sequentially (by IDs or league filter)
- Execution flow:
  1. Fetch target events (by IDs or league query)
  2. For each event: get features → agent.analyze() → save recommendation
  3. Sequential processing with 0.5s delay between events
  4. Returns summary stats (processed, saved, errors)

### No Unified Pipeline
- No orchestration layer for multiple agents
- No parallel agent execution
- No agent composition or chaining
- Single agent per runner instance

## 4. Existing Persistence Layer

### RecommendationRepository
- Located in `app/infrastructure/repositories/recommendation.py`
- SQLAlchemy-based data access
- Dependencies: `AsyncSession`
- Methods:
  - `create()`: Inserts recommendation, returns `RecommendationResponse`
  - `get_by_event_id()`: Returns list of `RecommendationORM` (legacy return type)
  - `get_recommendations()`: Filtered queries with pagination

### RecommendationCache
- Located in `app/infrastructure/cache/redis.py`
- Redis-based caching layer
- Dependencies: `RedisCacheClient`
- Methods:
  - `save_recommendation()`: Key-value storage (key: `rec:{event_id}`)
  - `get_recommendation()`: Cache retrieval
  - `add_to_list()` / `get_list()`: League-date indexed lists
  - `delete_recommendation()`: Cache invalidation
- TTL: 3 days default

### Storage Strategy
- Primary: PostgreSQL via SQLAlchemy ORM
- Cache: Redis for recommendations and league-date lists
- Write-through: Service layer writes to both DB and cache

## 5. Existing LLM Clients

### BaseLLMClient
- Located in `app/services/clients/base.py`
- Abstract interface for LLM providers
- Methods:
  - `generate()`: Structured output generation (Pydantic schema)
  - `get_model_id()`: Returns model identifier
  - `supports_json_mode()`: Feature flag for JSON mode

### OpenAIInstructorClient
- Located in `app/services/clients/openai_instructor.py`
- Fully implemented client using OpenAI + Instructor library
- Initialization: Requires `ModelConfig`
- Uses OpenRouter API (configurable base URL, API key, headers)
- Supports structured output via Instructor
- Handles JSON mode based on model config

### LangChainClient
- Located in `app/services/clients/langchain_client.py`
- Stub implementation (raises `NotImplementedError`)
- Placeholder for future LangChain integration

### LiteLLMClient
- Located in `app/services/clients/litellm_client.py`
- Stub implementation (raises `NotImplementedError`)
- Placeholder for future LiteLLM integration

### Client Factory
- Located in `app/services/clients/factory.py`
- Function: `create_llm_client(model_name: str = None)`
- Logic: Reads `ModelRegistry` → selects model config → instantiates client based on `settings.llm_client` type
- Supported types: "instructor", "langchain", "litellm" (only instructor works)

## 6. Existing Tasks / Schedulers

### TaskIQ Broker
- Located in `app/tasks/broker.py`
- Redis-based task queue using `ListQueueBroker`
- Separate Redis instances: `redis_broker_url` (tasks), `redis_cache_url` (cache)
- Lifecycle hooks: Container initialization on worker startup/shutdown

### run_batch_task
- Located in `app/tasks/run_batch.py`
- TaskIQ task decorator: `@broker.task()`
- Parameters: `event_ids`, `league`, `from_date`, `to_date`, `prompt_template`
- Execution: Creates DI container → instantiates services → processes events → saves recommendations
- Returns: Status dict with processed count and event results

### Scheduler
- Located in `boot/scheduler.py`
- TaskIQ scheduler using `LabelScheduleSource`
- No scheduled tasks defined (empty scheduler)

### Worker
- Located in `boot/worker.py`
- TaskIQ worker entry point
- Container lifecycle managed via broker events

## 7. Identified Gaps

### Architecture
- No unified pipeline/orchestration layer
- Duplicate feature extraction logic (`FeatureService` vs `FeatureBuilder`)
- Mixed dependency injection: Container pattern exists but not consistently used
- Legacy methods marked with `# TODO: LEGACY` in service layer

### Agent System
- Only one agent implementation (`LLMAgent`)
- No agent composition or multi-agent workflows
- No agent registry or discovery mechanism
- Agent interface minimal (only `analyze()` and `get_model_version()`)

### LLM Integration
- Two client stubs not implemented (LangChain, LiteLLM)
- Single active client (OpenAIInstructor)
- Model registry exists but limited usage

### Persistence
- Repository returns mixed types (`RecommendationORM` vs `RecommendationResponse`)
- Cache and DB writes not transactional
- No cache invalidation strategy documented

### Tasks & Scheduling
- Scheduler configured but no scheduled tasks defined
- Task execution creates new container per task (no shared state)
- No task retry or error handling strategy visible

### API Layer
- Routes exist but dependency injection inconsistent (`Depends()` mixed with manual instantiation)
- No unified error handling
- Legacy endpoints still present

