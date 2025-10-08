from typing import Dict, Any, Optional
import structlog

from app.services.prompts.loader import PromptLoader, PromptTemplate

logger = structlog.get_logger()


class PromptProcessor:
    def __init__(self, prompts_dir: str = "prompts"):
        self.loader = PromptLoader(prompts_dir)

    def prepare_prompt(
        self, template_name: str, features: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        template = self.loader.get_template(template_name)

        if not template:
            logger.error("template_not_found", template_name=template_name)
            return None

        try:
            context = self._prepare_context(features)

            user_prompt = template.format_user_prompt(**context)

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

            logger.info(
                "prompt_prepared",
                template=template_name,
                version=template.version,
            )

            return prompt_data

        except Exception as e:
            logger.error("prompt_preparation_failed", template=template_name, error=str(e))
            return None

    def _prepare_context(self, features: Dict[str, Any]) -> Dict[str, Any]:
        context = {
            "league_name": features.get("league_name", "N/A"),
            "home_team": features.get("home_team", "N/A"),
            "away_team": features.get("away_team", "N/A"),
            "commence_time": str(features.get("commence_time", "N/A")),
            "home_odds_avg": self._format_odds(features.get("home_odds_avg")),
            "draw_odds_avg": self._format_odds(features.get("draw_odds_avg")),
            "away_odds_avg": self._format_odds(features.get("away_odds_avg")),
            "home_odds_best": self._format_odds(features.get("home_odds_best")),
            "away_odds_best": self._format_odds(features.get("away_odds_best")),
            "draw_odds_best": self._format_odds(features.get("draw_odds_best")),
            "bookmakers_count": features.get("bookmakers_count", 0),
        }

        home_prob = self._calculate_implied_probability(features.get("home_odds_avg"))
        draw_prob = self._calculate_implied_probability(features.get("draw_odds_avg"))
        away_prob = self._calculate_implied_probability(features.get("away_odds_avg"))

        context["home_probability"] = f"{home_prob:.1f}" if home_prob else "N/A"
        context["draw_probability"] = f"{draw_prob:.1f}" if draw_prob else "N/A"
        context["away_probability"] = f"{away_prob:.1f}" if away_prob else "N/A"

        return context

    def _format_odds(self, odds: Optional[float]) -> str:
        if odds is None or odds == 0:
            return "N/A"
        return f"{odds:.2f}"

    def _calculate_implied_probability(self, odds: Optional[float]) -> Optional[float]:
        if odds is None or odds <= 0:
            return None
        return (1 / odds) * 100

    def list_available_templates(self) -> Dict[str, str]:
        return self.loader.list_templates()

    def reload_templates(self) -> None:
        self.loader.reload()
