"""
AI models configuration loader.

Loads LLM configurations from config/ai_models/ directory.
Separate from provider_policy to keep concerns isolated.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
import structlog
import yaml

logger = structlog.get_logger()


class AIConfigLoader:
    """Loader for AI model configurations."""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize AI config loader.

        Args:
            config_dir: Path to ai_models config directory.
                       Defaults to odds-service/config/ai_models/
        """
        if config_dir is None:
            service_root = Path(__file__).parent.parent.parent.parent
            config_dir = service_root / "config" / "ai_models"

        self.config_dir = Path(config_dir)
        self.prompts_dir = self.config_dir / "prompts"
        self._config_cache: Optional[Dict[str, Any]] = None

        logger.info(
            "ai_config_loader_initialized",
            config_dir=str(self.config_dir),
            prompts_dir=str(self.prompts_dir)
        )

    def load_models_config(self) -> Dict[str, Any]:
        """
        Load models.yml configuration.

        Returns:
            Dictionary with providers, models, retry config, etc.
        """
        if self._config_cache is not None:
            return self._config_cache

        models_file = self.config_dir / "models.yml"

        if not models_file.exists():
            logger.error("models_config_not_found", path=str(models_file))
            raise FileNotFoundError(f"AI models config not found: {models_file}")

        try:
            with open(models_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            self._config_cache = config

            logger.info(
                "ai_models_config_loaded",
                providers=list(config.get("providers", {}).keys()),
                default_provider=config.get("default_provider"),
                default_model=config.get("default_model")
            )

            return config

        except yaml.YAMLError as e:
            logger.error("failed_to_parse_models_config", error=str(e))
            raise ValueError(f"Invalid YAML in models.yml: {e}")

    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """
        Get configuration for specific provider.

        Args:
            provider: Provider name (e.g., 'openai', 'anthropic')

        Returns:
            Provider configuration dict
        """
        config = self.load_models_config()
        providers = config.get("providers", {})

        if provider not in providers:
            available = list(providers.keys())
            raise ValueError(f"Provider '{provider}' not found. Available: {available}")

        return providers[provider]

    def get_model_config(self, provider: str, model: str) -> Dict[str, Any]:
        """
        Get configuration for specific model.

        Args:
            provider: Provider name
            model: Model name

        Returns:
            Model configuration dict
        """
        provider_config = self.get_provider_config(provider)
        models = provider_config.get("models", {})

        if model not in models:
            available = list(models.keys())
            raise ValueError(
                f"Model '{model}' not found for provider '{provider}'. "
                f"Available: {available}"
            )

        return models[model]

    def get_default_provider_and_model(self) -> tuple[str, str]:
        """
        Get default provider and model from config.

        Returns:
            Tuple of (provider, model)
        """
        config = self.load_models_config()
        provider = config.get("default_provider", "openai")
        model = config.get("default_model", "gpt-4o-mini")

        return provider, model

    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get API key for provider from environment.

        Args:
            provider: Provider name

        Returns:
            API key from environment variable, or None if not set
        """
        provider_config = self.get_provider_config(provider)
        env_var = provider_config.get("api_key_env")

        if not env_var:
            logger.warning("no_api_key_env_var_configured", provider=provider)
            return None

        api_key = os.getenv(env_var)

        if not api_key:
            logger.warning("api_key_not_set", provider=provider, env_var=env_var)
            return None

        logger.debug("api_key_loaded", provider=provider, env_var=env_var)
        return api_key

    def get_retry_config(self) -> Dict[str, Any]:
        """
        Get retry configuration.

        Returns:
            Retry config dict with max_attempts, delays, retriable_status_codes
        """
        config = self.load_models_config()
        return config.get("retry_config", {})

    def get_timeout(self) -> int:
        """
        Get default timeout in seconds.

        Returns:
            Timeout in seconds
        """
        config = self.load_models_config()
        return config.get("timeout_sec", 60)

    def load_prompt(self, prompt_name: str) -> str:
        """
        Load prompt template from prompts directory.

        Args:
            prompt_name: Name of prompt file (without extension)

        Returns:
            Prompt content as string
        """
        for ext in [".txt", ".md"]:
            prompt_file = self.prompts_dir / f"{prompt_name}{ext}"
            if prompt_file.exists():
                try:
                    with open(prompt_file, "r", encoding="utf-8") as f:
                        content = f.read()

                    logger.debug("prompt_loaded", prompt_name=prompt_name, file=str(prompt_file))
                    return content

                except Exception as e:
                    logger.error("failed_to_load_prompt", prompt_name=prompt_name, error=str(e))
                    raise

        raise FileNotFoundError(f"Prompt not found: {prompt_name} (.txt or .md)")

    def list_available_prompts(self) -> list[str]:
        """
        List all available prompts in prompts directory.

        Returns:
            List of prompt names (without extensions)
        """
        if not self.prompts_dir.exists():
            return []

        prompts = set()
        for file in self.prompts_dir.iterdir():
            if file.is_file() and file.suffix in [".txt", ".md"]:
                prompts.add(file.stem)

        return sorted(prompts)


_ai_config_loader: Optional[AIConfigLoader] = None


def get_ai_config_loader() -> AIConfigLoader:
    """
    Get singleton AI config loader instance.

    Returns:
        AIConfigLoader instance
    """
    global _ai_config_loader

    if _ai_config_loader is None:
        _ai_config_loader = AIConfigLoader()

    return _ai_config_loader
