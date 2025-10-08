from typing import Dict, Any, Optional
from uuid import UUID
import json
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

from app.services.agents.base import Agent, AgentPrediction
from app.config.settings import settings

logger = structlog.get_logger()


class OpenRouterLLMAgent(Agent):
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.model = settings.openrouter_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        self.timeout = settings.llm_timeout

    def get_model_version(self) -> str:
        return f"{self.model}_v1"

    def _build_prompt(self, features: Dict[str, Any]) -> str:
        prompt = f"""You are an expert sports betting analyst. Analyze the following football match and provide a betting recommendation.

Match Details:
- League: {features.get('league_name', 'N/A')}
- Home Team: {features.get('home_team', 'N/A')}
- Away Team: {features.get('away_team', 'N/A')}
- Match Time: {features.get('commence_time', 'N/A')}

Odds Data (h2h market):
- Home Win Average Odds: {features.get('home_odds_avg', 'N/A')}
- Draw Average Odds: {features.get('draw_odds_avg', 'N/A')}
- Away Win Average Odds: {features.get('away_odds_avg', 'N/A')}
- Home Win Best Odds: {features.get('home_odds_best', 'N/A')}
- Away Win Best Odds: {features.get('away_odds_best', 'N/A')}
- Number of Bookmakers: {features.get('bookmakers_count', 'N/A')}

Based on this data, provide your analysis in the following JSON format:
{{
    "pick": "home|draw|away",
    "confidence": 0.0-1.0,
    "explanation": "Brief explanation (max 200 chars)"
}}

Consider the odds, implied probabilities, and market consensus. Be objective and data-driven."""

        return prompt

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _call_llm(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a professional sports betting analyst."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }

            logger.info("calling_llm", model=self.model)

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

            prompt = self._build_prompt(event_features)
            response = await self._call_llm(prompt)
            prediction = self._parse_response(response, event_id)

            if prediction:
                logger.info(
                    "prediction_generated",
                    event_id=str(event_id),
                    pick=prediction.pick,
                    confidence=prediction.confidence,
                )

            return prediction

        except Exception as e:
            logger.error("analysis_failed", error=str(e))
            return None
