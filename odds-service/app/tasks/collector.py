from typing import Dict
import structlog
from prometheus_client import Counter, Histogram

from app.config import settings
from app.infrastructure.http.odds_api import OddsAPIClient
from app.infrastructure.di.dependencies import get_task_session
from app.utils.time_utils import now_utc
from app.infrastructure.di.dependencies import get_sports_service
from app.infrastructure.repositories import SportRepository, CompetitionsRepository
from app.tasks.normalizer import OddsNormalizer
from app.tasks.broker import broker

logger = structlog.get_logger()

collection_duration = Histogram("odds_collection_duration_seconds", "Time spent collecting odds data")
events_processed_total = Counter("odds_events_processed_total", "Total number of events processed")
collection_errors_total = Counter("odds_collection_errors_total", "Total number of collection errors")


@broker.task(schedule=[{"cron": "0 9 * * *"}, {"cron": "0 19 * * *"}])
async def collect_odds_task() -> Dict[str, str]:
    start_time = now_utc()
    logger.info("collection_task_started", timestamp=start_time.isoformat())

    api_adapter = OddsAPIClient(
        api_key=settings.odds_api_key,
        base_url=settings.odds_api_base_url,
        regions=settings.odds_api_regions,
        markets=settings.odds_api_markets,
    )

    try:
        # Use dependency injection for database session
        session = await get_task_session()
        try:
            sport_repo = SportRepository(session)
            competition_repo = CompetitionsRepository(session)
            normalizer = OddsNormalizer(session)

            sport_id = await sport_repo.get_or_create("soccer")

            total_processed = 0

            for competition_key in settings.odds_api_competitions:
                logger.info("collecting_competition", competition=competition_key)

                competition_id = await competition_repo.get_or_create(
                    sport_id=sport_id,
                    provider_key=competition_key,
                    title=competition_key.replace("_", " ").title(),
                    description=f"Competition for {competition_key}",
                )

                odds_data = await api_adapter.get_odds(
                    sport=competition_key,
                    regions=settings.odds_api_regions,
                    markets=settings.odds_api_markets,
                )

                events_processed = 0
                for event_data in odds_data:
                    event_id = await normalizer.process_event_data(event_data, sport_id, competition_id)
                    if event_id:
                        events_processed += 1

                logger.info("competition_processed", competition=competition_key, events_count=events_processed)
                events_processed_total.inc(events_processed)
                total_processed += events_processed

            await session.commit()
        finally:
            await session.close()

        duration = (now_utc() - start_time).total_seconds()
        collection_duration.observe(duration)

        logger.info(
            "collection_task_completed",
            total_events=total_processed,
            duration_seconds=duration,
        )

        return {
            "status": "success",
            "total_events": str(total_processed),
            "timestamp": now_utc().isoformat(),
        }

    except Exception as e:
        logger.error("collection_task_failed", error=str(e))
        collection_errors_total.inc()
        return {"status": "error", "message": str(e)}

    finally:
        await api_adapter.close()

@broker.task(schedule=[{"cron": "0 9 * * *"}, {"cron": "0 19 * * *"}])
async def collect_sports_task() -> Dict[str, str]:
    """
    Collect and sync sports data from external provider.
    
    This task is now thin and delegates to SportsService.
    """
    start_time = now_utc()
    logger.info("sports_collection_task_started", timestamp=start_time.isoformat())

    try:
        # Get sports service - it manages its own session lifecycle
        sports_service = await get_sports_service()
        
        # Delegate to service for business logic
        result = await sports_service.sync_sports_and_competitions()
        
        duration = (now_utc() - start_time).total_seconds()
        collection_duration.observe(duration)
        
        logger.info(
            "sports_collection_task_completed",
            duration_seconds=duration,
            **result
        )
        
        # Handle new nested result structure
        categories_count = result.get("categories", {}).get("synced_count", 0)
        competitions_count = result.get("competitions", {}).get("synced_count", 0)
        
        return {
            "status": result["status"],
            "categories_synced": str(categories_count),
            "competitions_synced": str(competitions_count),
            "timestamp": now_utc().isoformat(),
        }

    except Exception as e:
        logger.error("sports_collection_task_failed", error=str(e))
        collection_errors_total.inc()
        return {"status": "error", "message": str(e)}
