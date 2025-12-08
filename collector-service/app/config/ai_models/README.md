# AI Models Configuration

This directory contains AI/LLM model configurations and prompts, **separate from provider_policy.yml**.

## Structure

```
config/ai_models/
├── models.yml              # LLM provider and model configurations
├── prompts/                # Prompt templates
│   ├── system_default.txt  # Default system prompt
│   └── ...
└── README.md
```

## Configuration

### models.yml

Defines available LLM providers (OpenAI, Anthropic, etc.) and their models with:
- Context window size
- Max output tokens
- Temperature settings
- Feature support (streaming, function calling)
- Retry and timeout configurations

Example:
```yaml
providers:
  openai:
    api_key_env: OPENAI_API_KEY
    base_url: https://api.openai.com/v1
    models:
      gpt-4o-mini:
        context_window: 128000
        max_output_tokens: 16384
        temperature: 0.7

default_provider: openai
default_model: gpt-4o-mini
```

### API Keys

API keys are loaded from environment variables:
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key

## Usage

### Basic LLM Service Usage

```python
from app.infrastructure.factory import get_llm_service

# Get service from DI
llm_service = await get_llm_service()

# Simple completion
response = await llm_service.complete(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain betting odds."}
    ]
)

print(response.content)
```

### Using System Prompts

```python
# Use default system prompt
response = await llm_service.complete_with_system_prompt(
    user_message="Analyze this event: Real Madrid vs Barcelona",
    system_prompt_name="system_default"
)
```

### Using Prompt Templates

```python
# Create template in prompts/analysis.txt:
# Event: {event_name}
# Teams: {home} vs {away}
# Analyze the matchup...

response = await llm_service.complete_with_template(
    template_name="analysis",
    template_vars={
        "event_name": "UEFA Champions League Final",
        "home": "Real Madrid",
        "away": "Barcelona"
    }
)
```

### From Container

```python
from app.tasks.broker import broker

# In TaskIQ task
container = broker.state.container
llm_service = container.llm_service

# Or create new instance
llm_service = container.create_llm_service()
```

### AI Config Loader

```python
from app.infrastructure.ai.config_loader import get_ai_config_loader

loader = get_ai_config_loader()

# Load configuration
provider, model = loader.get_default_provider_and_model()
model_config = loader.get_model_config(provider, model)
api_key = loader.get_api_key(provider)

# Load prompts
system_prompt = loader.load_prompt("system_default")
prompts_list = loader.list_available_prompts()
```

## Architecture

```
app/infrastructure/ai/
├── __init__.py
├── config_loader.py        # Configuration loader
└── clients/
    ├── __init__.py
    └── base.py             # BaseLLMClient interface

app/services/
└── llm_service.py          # LLM business logic service

app/infrastructure/di/
├── container.py            # DI container with ai_config, llm_service
└── services.py             # get_llm_service() factory
```

## Design Principles

1. **Separation of Concerns**: AI config is separate from provider_policy.yml
2. **DI Integration**: Services available through dependency injection
3. **Retry Logic**: Built-in retry with exponential backoff
4. **Prompt Management**: Centralized prompt templates
5. **Type Safety**: Pydantic models for requests/responses

## Next Steps (T2)

In T2, add concrete LLM client implementations:
- `OpenAIClient` - OpenAI API wrapper
- `AnthropicClient` - Anthropic API wrapper
- Client factory for automatic provider selection
