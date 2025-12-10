from typing import Dict, Type, Callable
import structlog

from app.config.model_loader import ModelConfig, ModelRegistry
from app.config.settings import settings
from app.llm.base import BaseLLMClient
from app.llm.clients.openai_instructor import OpenAIInstructorClient
from app.llm.clients.langchain_client import LangChainClient
from app.llm.clients.litellm_client import LiteLLMClient

logger = structlog.get_logger()

# TODO: legacy
def create_llm_client(model_name: str = None) -> BaseLLMClient:
    registry = ModelRegistry(settings.models_config_full_path)

    model_config = registry.get_model(model_name or settings.active_model_name)

    if not model_config:
        logger.error("model_not_found", name=model_name or settings.active_model_name)
        raise ValueError(f"Model {model_name or settings.active_model_name} not found in registry")

    client_type = settings.llm_client

    if client_type == "instructor":
        return OpenAIInstructorClient(model_config)
    elif client_type == "langchain":
        return LangChainClient(model_config)
    elif client_type == "litellm":
        return LiteLLMClient(model_config)
    else:
        logger.error("unknown_client_type", client_type=client_type)
        raise ValueError(f"Unknown LLM client type: {client_type}")

def create_all_clients(
    registry: ModelRegistry,
) -> Dict[str, BaseLLMClient]:
    """
    Create LLM clients for all models in registry.
    
    Args:
        registry: ModelRegistry instance containing all model configurations
        
    Returns:
        Dictionary mapping model names to BaseLLMClient instances
    """
    clients: Dict[str, BaseLLMClient] = {}
    
    for model_config in registry.models.values():
        provider = model_config.provider
        client = select_client_by_provider(provider, model_config)
        clients[model_config.name] = client
        logger.debug(
            "client_created",
            model_name=model_config.name,
            provider=provider,
            model_id=model_config.model_id,
        )
    
    logger.debug("all_clients_created", total_count=len(clients))
    return clients


def select_client_by_provider(
    provider: str, model_config: ModelConfig
) -> BaseLLMClient:
    """
    Select and instantiate client based on provider.
    
    Args:
        provider: Provider identifier ("instructor", "langchain", "litellm", "openrouter")
        model_config: Model configuration instance
        
    Returns:
        BaseLLMClient instance for the specified provider
    """
    provider_map: Dict[str, Callable[[ModelConfig], BaseLLMClient]] = {
        "instructor": OpenAIInstructorClient,
        "langchain": LangChainClient,
        "litellm": LiteLLMClient,
        "openrouter": LiteLLMClient,
    }
    
    client_class = provider_map.get(provider)
    if not client_class:
        logger.error("unknown_provider", provider=provider)
        raise ValueError(f"Unknown provider: {provider}")
    
    client = client_class(model_config)
    logger.debug(
        "client_selected",
        provider=provider,
        model_id=model_config.model_id,
    )
    return client
