from typing import Dict, Any, Optional
from uuid import UUID
import json
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

from app.services.agents.base import Agent, AgentPrediction
from app.services.prompts.processor import PromptProcessor
from app.config.settings import settings

logger = structlog.get_logger()


class OpenRouterLLMAgent(Agent):
    def __init__(self, prompt_template: str = "betting_analysis"):
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.model = settings.openrouter_model
        self.timeout = settings.llm_timeout
        self.prompt_template = prompt_template
        self.prompt_processor = PromptProcessor(prompts_dir="prompts")

    def get_model_version(self) -> str:
        return f"{self.model}_{self.prompt_template}_v1"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _call_llm(
        self, system_prompt: str, user_prompt: str, parameters: Dict[str, Any]
    ) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": parameters.get("temperature", 0.7),
                "max_tokens": parameters.get("max_tokens", 500),
                "top_p": parameters.get("top_p", 1.0),
            }

            logger.info(
                "calling_llm",
                model=self.model,
                template=self.prompt_template,
                temperature=payload["temperature"],
            )

            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )

            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]
            logger.info("llm_response_received", model=self.model)

            return content

    def _parse_response(self, response: str, event_id: UUID) -> Optional[AgentPrediction]:
        try:
            response_clean = response.strip()
            if response_clean.startswith("```json"):
                response_clean = response_clean[7:]
            if response_clean.endswith("```"):
                response_clean = response_clean[:-3]
            response_clean = response_clean.strip()

            data = json.loads(response_clean)

            pick = data.get("pick", "").lower()
            if pick not in ["home", "draw", "away"]:
                logger.warning("invalid_pick", pick=pick)
                return None

            confidence = float(data.get("confidence", 0.0))
            if not (0.0 <= confidence <= 1.0):
                logger.warning("invalid_confidence", confidence=confidence)
                confidence = max(0.0, min(1.0, confidence))

            explanation = data.get("explanation", "")[:200]

            return AgentPrediction(
                event_id=event_id,
                pick=pick,
                confidence=confidence,
                explanation=explanation,
                model_version=self.get_model_version(),
            )

        except Exception as e:
            logger.error("failed_to_parse_llm_response", error=str(e), response=response[:200])
            return None

    async def analyze(self, event_features: Dict[str, Any]) -> Optional[AgentPrediction]:
        try:
            event_id = UUID(str(event_features.get("external_id")))

            if "home_odds_avg" not in event_features or event_features["home_odds_avg"] is None:
                logger.warning("insufficient_data", event_id=str(event_id))
                return None

            prompt_data = self.prompt_processor.prepare_prompt(
                template_name=self.prompt_template, features=event_features
            )

            if not prompt_data:
                logger.error("prompt_preparation_failed", template=self.prompt_template)
                return None

            response = await self._call_llm(
                system_prompt=prompt_data["system_prompt"],
                user_prompt=prompt_data["user_prompt"],
                parameters=prompt_data["parameters"],
            )

            prediction = self._parse_response(response, event_id)

            if prediction:
                logger.info(
                    "prediction_generated",
                    event_id=str(event_id),
                    pick=prediction.pick,
                    confidence=prediction.confidence,
                    template=self.prompt_template,
                )

            return prediction

        except Exception as e:
            logger.error("analysis_failed", error=str(e), template=self.prompt_template)
            return None
