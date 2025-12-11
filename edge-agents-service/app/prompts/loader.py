from pathlib import Path
from typing import Dict, Any, Optional
import yaml
import structlog

logger = structlog.get_logger()


class PromptTemplate:
    def __init__(self, data: Dict[str, Any]):
        self.name = data.get("name", "unknown")
        self.version = data.get("version", "1.0")
        self.description = data.get("description", "")
        self.system_prompt = data.get("system_prompt", "")
        self.user_prompt_template = data.get("user_prompt_template", "")
        self.parameters = data.get("parameters", {})
        self.model_preference = data.get("model_preference")
        raw_params = data.get("parameters", {})
        self.parameters = {
            "temperature": float(raw_params.get("temperature", 0.7)),
            "max_tokens": int(raw_params.get("max_tokens", 500)),
            "top_p": float(raw_params.get("top_p", 1.0)),
        }

    def format_user_prompt(self, **kwargs: Any) -> str:
        try:
            return self.user_prompt_template.format(**kwargs)
        except KeyError as e:
            logger.error("missing_template_variable", variable=str(e), template=self.name)
            raise ValueError(f"Missing template variable: {e}")

    def get_temperature(self) -> float:
        return self.parameters.get("temperature", 0.4)

    def get_max_tokens(self) -> int:
        return self.parameters.get("max_tokens", 500)

    def get_top_p(self) -> float:
        return self.parameters.get("top_p", 0.1)


class PromptLoader:
    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = Path(prompts_dir)
        self.templates: Dict[str, PromptTemplate] = {}
        self._load_all_prompts()

    def _load_all_prompts(self) -> None:
        if not self.prompts_dir.exists():
            logger.warning("prompts_directory_not_found", path=str(self.prompts_dir))
            return

        for yaml_file in self.prompts_dir.glob("*.yml"):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                template = PromptTemplate(data)
                self.templates[template.name] = template

                logger.info(
                    "prompt_loaded",
                    name=template.name,
                    version=template.version,
                    file=yaml_file.name,
                )

            except Exception as e:
                logger.error("failed_to_load_prompt", file=yaml_file.name, error=str(e))

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        template = self.templates.get(name)

        if not template:
            logger.warning("prompt_template_not_found", name=name)
            return None

        return template

    def list_templates(self) -> Dict[str, str]:
        return {name: template.description for name, template in self.templates.items()}

    def reload(self) -> None:
        logger.info("reloading_prompts")
        self.templates.clear()
        self._load_all_prompts()
