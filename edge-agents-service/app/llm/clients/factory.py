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
    client_type: str
) -> Dict[str, BaseLLMClient]:
    """
    Create LLM clients for all models in registry.
    
    Args:
        registry: ModelRegistry instance containing all model configurations
        client_type: Client type to use for all models
    Returns:
        Dictionary mapping model names to BaseLLMClient instances
    """
    clients: Dict[str, BaseLLMClient] = {}
    
    for model_config in registry.models.values():
        client = select_client_by_provider(client_type, model_config)
        clients[model_config.model_id] = client
        logger.debug(
            "client_created",
            model_name=model_config.name,
            client_type=client_type,
            model_id=model_config.model_id,
        )
    
    logger.debug("all_clients_created", total_count=len(clients))
    return clients


def select_client_by_provider(
    client_type: str, model_config: ModelConfig
) -> BaseLLMClient:
    """
    Select and instantiate client based on provider.
    
    Args:
        client_type: Provider identifier ("instructor", "langchain", "litellm", "openrouter")
        model_config: Model configuration instance
        
    Returns:
        BaseLLMClient instance for the specified provider
    """
    client_map: Dict[str, Callable[[ModelConfig], BaseLLMClient]] = {
        "instructor": OpenAIInstructorClient,
        "langchain": LangChainClient,
        "litellm": LiteLLMClient,
        "openrouter": LiteLLMClient,
    }
    
    client_class = client_map.get(client_type)
    if not client_class:
        logger.error("unknown_client_type", client_type=client_type)
        raise ValueError(f"Unknown client type: {client_type}")
    
    client = client_class(model_config)
    logger.debug(
        "client_selected",
        client_type=client_type,
        model_id=model_config.model_id,
    )
    return client
