from typing import Dict, Any, Optional
from uuid import UUID
import structlog

from app.agents.base import Agent, AgentPrediction
from app.llm.clients.base import BaseLLMClient
from app.services.prompts.processor import PromptProcessor
from app.domain.entities.recommendation import RecommendationSchema

logger = structlog.get_logger()


class LLMAgent(Agent):
    def __init__(self, llm_client: BaseLLMClient, prompt_template: str = "betting_analysis"):
        self.llm_client = llm_client
        self.prompt_template = prompt_template
        self.prompt_processor = PromptProcessor(prompts_dir="prompts")

    def get_model_version(self) -> str:
        return f"{self.llm_client.get_model_id()}_{self.prompt_template}_v2"

    async def analyze(self, event_features: Dict[str, Any]) -> Optional[AgentPrediction]:
        try:
            event_id = UUID(str(event_features.get("external_id")))

            if "home_odds_avg" not in event_features or event_features["home_odds_avg"] is None:
                logger.warning("insufficient_data", event_id=str(event_id))
                return None

            prompt_data = self.prompt_processor.prepare_prompt(
                template_name=self.prompt_template,
                features=event_features
            )

            if not prompt_data:
                logger.error("prompt_preparation_failed", template=self.prompt_template)
                return None

            recommendation = await self.llm_client.generate(
                schema=RecommendationSchema,
                prompt=prompt_data["user_prompt"],
                system_prompt=prompt_data["system_prompt"],
                temperature=prompt_data["parameters"].get("temperature"),
                max_tokens=prompt_data["parameters"].get("max_tokens"),
            )

            prediction = AgentPrediction(
                event_id=event_id,
                pick=recommendation.pick,
                confidence=recommendation.confidence,
                explanation=recommendation.short_explanation,
                reasoning=recommendation.reasoning,
                model_version=self.get_model_version(),
            )

            logger.info(
                "prediction_generated",
                event_id=str(event_id),
                pick=prediction.pick,
                confidence=prediction.confidence,
                model=self.llm_client.get_model_id(),
                template=self.prompt_template,
            )

            return prediction

        except Exception as e:
            logger.error(
                "analysis_failed",
                error=str(e),
                template=self.prompt_template,
                model=self.llm_client.get_model_id(),
            )
            return None
