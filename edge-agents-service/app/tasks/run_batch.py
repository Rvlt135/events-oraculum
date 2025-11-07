from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
import structlog

from app.config.settings import settings
from app.db.pg import AsyncSessionLocal
from app.services.clients.factory import create_llm_client
from app.cache.redis import recommendation_cache
from app.models.recommendation import RecommendationCreate
from app.services.agents.persistence import RecommendationPersistence
from app.services.agents.llm_agent import LLMAgent
from app.services.features import FeatureService
from app.tasks.broker import broker

logger = structlog.get_logger()


@broker.task
async def run_batch_task(
    event_ids: Optional[List[str]] = None,
    league: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    prompt_template: str = "betting_analysis"
) -> Dict[str, Any]:
    try:
        logger.info("run_batch_task_started", event_ids=event_ids, league=league)

        if not recommendation_cache.client:
            await recommendation_cache.initialize()

        async with AsyncSessionLocal() as session:
            persistence = RecommendationPersistence(session, recommendation_cache)

            llm_client = create_llm_client(settings.active_model_name)

            agent = LLMAgent(
                llm_client=llm_client,
                prompt_template=prompt_template
            )

            feature_service = FeatureService(session)

            processed_events = []

            if event_ids:
                for event_id_str in event_ids:
                    try:
                        event_id = UUID(event_id_str)

                        features = await feature_service.get_event_features(event_id)

                        if not features:
                            logger.warning("no_features_found", event_id=event_id_str)
                            continue

                        result = await agent.analyze(features)

                        recommendation = RecommendationCreate(
                            event_id=event_id,
                            league_key=features.get("league_key", "unknown"),
                            pick=result.pick,
                            confidence=result.confidence,
                            short_explanation=result.short_explanation,
                            reasoning=result.reasoning,
                            model_version=result.model_version
                        )

                        saved = await persistence.save_recommendation(recommendation)

                        processed_events.append({
                            "event_id": event_id_str,
                            "rec_id": str(saved.rec_id),
                            "pick": saved.pick,
                            "confidence": saved.confidence
                        })

                        logger.info("event_processed", event_id=event_id_str, pick=saved.pick)

                    except Exception as e:
                        logger.error("event_processing_error", event_id=event_id_str, error=str(e))
                        continue

            await session.commit()

        logger.info("run_batch_task_completed", processed_count=len(processed_events))

        return {
            "status": "success",
            "processed": len(processed_events),
            "events": processed_events,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error("run_batch_task_failed", error=str(e))
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
