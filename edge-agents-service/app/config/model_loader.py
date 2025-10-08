from typing import Dict, Any, Optional
from pathlib import Path
import yaml
import structlog

logger = structlog.get_logger()


class ModelConfig:
    def __init__(self, data: Dict[str, Any]):
        self.name = data["name"]
        self.provider = data["provider"]
        self.model_id = data["model_id"]
        self.supports_json_mode = data.get("supports_json_mode", False)
        self.max_context = data.get("max_context", 4096)
        self.temperature_default = data.get("temperature_default", 0.7)
        self.max_tokens_default = data.get("max_tokens_default", 500)
        self.tags = data.get("tags", [])
        self.description = data.get("description", "")


class ModelRegistry:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.models: Dict[str, ModelConfig] = {}
        self.default_model_name: str = ""
        self._load()

    def _load(self) -> None:
        if not self.config_path.exists():
            logger.warning("models_config_not_found", path=str(self.config_path))
            return

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        for model_data in data.get("models", []):
            model = ModelConfig(model_data)
            self.models[model.name] = model

        self.default_model_name = data.get("default_model", "gpt-4o-mini")

        logger.info(
            "models_loaded",
            count=len(self.models),
            default=self.default_model_name,
        )

    def get_model(self, name: Optional[str] = None) -> Optional[ModelConfig]:
        model_name = name or self.default_model_name

        if model_name not in self.models:
            logger.warning("model_not_found", name=model_name)
            return None

        return self.models[model_name]

    def list_models(self) -> Dict[str, str]:
        return {name: model.description for name, model in self.models.items()}
