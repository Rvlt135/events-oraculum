from typing import Dict, Any
import structlog

from app.prompts.loader import PromptLoader

logger = structlog.get_logger()


class PromptProcessor:
    def __init__(self, prompts_dir: str = "prompts"):
        self.loader = PromptLoader(prompts_dir)

    def prepare_prompt(
        self, template_name: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare prompt from template and context.
        
        Args:
            template_name: Name of the template to load
            context: Dictionary with values for template placeholders
            
        Returns:
            Dictionary with system_prompt, user_prompt, parameters, template_name, template_version
            
        Raises:
            ValueError: If template not found or context missing required placeholders
        """
        # 1. Load template
        template = self.loader.get_template(template_name)
        
        if not template:
            logger.warning("template_not_found", template_name=template_name)
            raise ValueError(f"Template '{template_name}' not found")
        
        # 2. Render user prompt
        try:
            user_prompt = template.user_prompt_template.format(**context)
        except KeyError as e:
            logger.error("missing_context_field", field=str(e), template=template_name)
            raise ValueError(f"Missing field in context: {e}")
        
        # 3. Build final dict
        prompt_data = {
            "system_prompt": template.system_prompt,
            "user_prompt": user_prompt,
            "parameters": {
                "temperature": template.get_temperature(),
                "max_tokens": template.get_max_tokens(),
                "top_p": template.get_top_p(),
            },
            "template_name": template.name,
            "template_version": template.version,
        }
        
        logger.info("prompt_prepared", template=template_name, version=template.version)
        
        return prompt_data

    def list_available_templates(self) -> Dict[str, str]:
        return self.loader.list_templates()

    def reload_templates(self) -> None:
        self.loader.reload()
