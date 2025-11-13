"""
AI models configuration loader.

Loads LLM configurations from app/config/ai_models/ directory.
Separate from provider_policy to keep concerns isolated.
"""
from pathlib import Path
from typing import Dict, Any, Optional, TYPE_CHECKING, List
import structlog
import yaml
from pydantic import BaseModel

if TYPE_CHECKING:
    from app.config.settings import Settings

logger = structlog.get_logger()


class RetryConfigDTO(BaseModel):
    """DTO for retry configuration."""
    max_attempts: int
    base_delay_sec: int
    max_delay_sec: int
    retriable_status_codes: List[int]
    special_delays: Dict[str, int] = {}  # status_code -> delay_sec


class AIConfigLoader:
    """Loader for AI model configurations."""

    def __init__(self, config_dir: Optional[Path] = None, settings: Optional["Settings"] = None):
        """
        Initialize AI config loader.

        Args:
            config_dir: Path to ai_models config directory.
                       Defaults to app/config/ai_models/
            settings: Settings instance for API keys and base URLs.
                     If None, will import from app.config.settings
        """
        if config_dir is None:
            app_root = Path(__file__).parent.parent.parent  # app/
            config_dir = app_root / "config" / "ai_models"  # app/config/ai_models/

        self.config_dir = Path(config_dir)
        self.prompts_dir = self.config_dir / "prompts"
        self._config_cache: Optional[Dict[str, Any]] = None

        # Import settings if not provided
        if settings is None:
            from app.config.settings import settings as app_settings
            self.settings = app_settings
        else:
            self.settings = settings

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
        
        Raises:
            ValueError: If default_provider or default_model not found in config
        """
        config = self.load_models_config()
        provider = config.get("default_provider")
        if not provider:
            raise ValueError("default_provider not found in models.yml")
        
        model = config.get("default_model")
        if not model:
            raise ValueError("default_model not found in models.yml")

        return provider, model

    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get API key for provider from settings.

        Args:
            provider: Provider name

        Returns:
            API key from settings, or None if not set
        """
        key_mapping = {
            "openrouter": "openrouter_api_key",
            "openai": "openai_api_key",
            "anthropic": "anthropic_api_key",
        }

        setting_key = key_mapping.get(provider)
        if not setting_key:
            logger.warning("unknown_provider_for_api_key", provider=provider)
            return None

        api_key = getattr(self.settings, setting_key, None)

        if not api_key:
            logger.warning("api_key_not_set", provider=provider, setting_key=setting_key)
            return None

        logger.debug("api_key_loaded", provider=provider, setting_key=setting_key)
        return api_key

    def get_base_url(self, provider: str) -> Optional[str]:
        """
        Get base URL for provider from settings.

        Args:
            provider: Provider name

        Returns:
            Base URL from settings, or None if not set
        """
        url_mapping = {
            "openrouter": "openrouter_base_url",
            "openai": "openai_base_url",
            "anthropic": "anthropic_base_url",
        }

        setting_key = url_mapping.get(provider)
        if not setting_key:
            logger.warning("unknown_provider_for_base_url", provider=provider)
            return None

        base_url = getattr(self.settings, setting_key, None)

        if not base_url:
            logger.warning("base_url_not_set", provider=provider, setting_key=setting_key)
            return None

        logger.debug("base_url_loaded", provider=provider, setting_key=setting_key)
        return base_url

    def get_retry_config(self) -> RetryConfigDTO:
        """
        Get retry configuration as DTO.

        Returns:
            RetryConfigDTO with max_attempts, delays, retriable_status_codes, special_delays
        
        Raises:
            ValueError: If retry_config not found in config or required fields missing
        """
        config = self.load_models_config()
        retry_config = config.get("retry_config")
        if retry_config is None:
            raise ValueError("retry_config not found in models.yml")
        
        try:
            return RetryConfigDTO(**retry_config)
        except Exception as e:
            raise ValueError(f"Invalid retry_config in models.yml: {e}")

    def get_timeout(self) -> int:
        """
        Get default timeout in seconds.

        Returns:
            Timeout in seconds
        
        Raises:
            ValueError: If timeout_sec not found in config
        """
        config = self.load_models_config()
        timeout = config.get("timeout_sec")
        if timeout is None:
            raise ValueError("timeout_sec not found in models.yml")
        return timeout

    def load_prompt_bundle(self, name: str) -> Dict[str, Any]:
        """
        Load prompt bundle from YAML file.

        Args:
            name: Name of prompt bundle (without extension)

        Returns:
            Dict with keys: system, instruction, schema (optional), mode_preference (optional)

        Raises:
            FileNotFoundError: If YAML file not found
            ValueError: If required fields are missing or invalid
        """
        for ext in [".yml", ".yaml"]:
            bundle_file = self.prompts_dir / f"{name}{ext}"
            if bundle_file.exists():
                try:
                    with open(bundle_file, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)

                    if not isinstance(data, dict):
                        raise ValueError(f"Invalid YAML format in {bundle_file}: expected dict")

                    # Validate required fields
                    if "system" not in data:
                        raise ValueError(f"Missing 'system' field in {bundle_file}")
                    if "instruction" not in data:
                        raise ValueError(f"Missing 'instruction' field in {bundle_file}")

                    result = {
                        "system": str(data["system"]),
                        "instruction": str(data["instruction"]),
                        "schema": data.get("schema"),
                        "mode_preference": data.get("mode_preference", []),
                    }

                    logger.debug(
                        "prompt_bundle_loaded",
                        name=name,
                        file=str(bundle_file),
                        with_schema=result["schema"] is not None
                    )

                    return result

                except yaml.YAMLError as e:
                    logger.error("failed_to_parse_prompt_bundle", name=name, error=str(e))
                    raise ValueError(f"Invalid YAML in {bundle_file}: {e}")
                except Exception as e:
                    logger.error("failed_to_load_prompt_bundle", name=name, error=str(e))
                    raise

        raise FileNotFoundError(f"Prompt bundle not found: {name} (.yml or .yaml)")

    def load_prompt(self, prompt_name: str) -> str:
        """
        DEPRECATED: Use load_prompt_bundle() instead.

        Load prompt template from prompts directory (legacy TXT/MD support).

        Args:
            prompt_name: Name of prompt file (without extension)

        Returns:
            Prompt content as string

        Raises:
            RuntimeError: Always, as TXT/MD prompts are deprecated
        """
        raise RuntimeError(
            f"TXT/MD prompts are deprecated. Use load_prompt_bundle('{prompt_name.split('.')[0]}') instead."
        )

    def list_available_prompts(self) -> list[str]:
        """
        List all available prompt bundles (YAML only).

        Returns:
            List of prompt bundle names (without extensions)
        """
        if not self.prompts_dir.exists():
            return []

        prompts = set()
        for file in self.prompts_dir.iterdir():
            if file.is_file() and file.suffix in [".yml", ".yaml"]:
                prompts.add(file.stem)

        return sorted(prompts)


_ai_config_loader: Optional[AIConfigLoader] = None


def get_ai_config_loader(settings: Optional["Settings"] = None) -> AIConfigLoader:
    """
    Get singleton AI config loader instance.

    Args:
        settings: Optional settings instance. If None, will import from app.config.settings

    Returns:
        AIConfigLoader instance
    """
    global _ai_config_loader

    if _ai_config_loader is None:
        _ai_config_loader = AIConfigLoader(settings=settings)

    return _ai_config_loader
