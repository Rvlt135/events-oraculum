from typing import List, Optional
from datetime import datetime
from uuid import UUID
import asyncio
import structlog

from app.services.features import FeatureBuilder
from app.services.agents.base import Agent
from app.services.agents.llm_openrouter import OpenRouterLLMAgent
from app.db.repositories import RecommendationRepository
from app.models.recommendation import RecommendationCreate
from app.config.settings import settings

logger = structlog.get_logger()


class AgentRunner:
    def __init__(self, repository: RecommendationRepository):
        self.repository = repository
        self.feature_builder = FeatureBuilder(settings.postgres_url)
        self.agent: Agent = OpenRouterLLMAgent()

    async def run_batch(
        self,
        event_ids: Optional[List[UUID]] = None,
        league: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> dict:
        await self.feature_builder.connect()

        try:
            if event_ids:
                target_events = event_ids
                logger.info("running_batch_for_events", count=len(event_ids))
            elif league:
                target_events = await self.feature_builder.get_events_by_league(
                    league, from_date, to_date
                )
                logger.info("running_batch_for_league", league=league, count=len(target_events))
            else:
                logger.warning("no_events_specified")
                return {"status": "error", "message": "No events specified"}

            if not target_events:
                logger.warning("no_events_found")
                return {"status": "success", "processed": 0, "saved": 0}

            processed = 0
            saved = 0
            errors = 0

            for event_id in target_events:
                try:
                    features = await self.feature_builder.get_event_features(event_id)

                    if not features:
                        logger.warning("features_not_found", event_id=str(event_id))
                        errors += 1
                        continue

                    prediction = await self.agent.analyze(features)

                    if prediction:
                        rec = RecommendationCreate(
                            event_id=event_id,
                            league_key=features.get("league_key", "unknown"),
                            pick=prediction.pick,
                            confidence=prediction.confidence,
                            short_explanation=prediction.explanation,
                            model_version=prediction.model_version,
                        )

                        await self.repository.create(rec)
                        saved += 1

                    processed += 1

                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.error("event_processing_error", event_id=str(event_id), error=str(e))
                    errors += 1

            logger.info(
                "batch_completed",
                total=len(target_events),
                processed=processed,
                saved=saved,
                errors=errors,
            )

            return {
                "status": "success",
                "total": len(target_events),
                "processed": processed,
                "saved": saved,
                "errors": errors,
            }

        finally:
            await self.feature_builder.disconnect()
