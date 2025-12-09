from app.config.settings import settings
from app.config.model_loader import ModelRegistry
from app.llm.clients.base import BaseLLMClient
from app.llm.clients.openai_instructor import OpenAIInstructorClient
from app.llm.clients.langchain_client import LangChainClient
from app.llm.clients.litellm_client import LiteLLMClient
import structlog

logger = structlog.get_logger()


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
