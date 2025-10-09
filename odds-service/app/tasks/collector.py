from datetime import datetime
from typing import Dict
import structlog
from prometheus_client import Counter, Histogram

from app.config import settings
from app.adapters.the_odds_api import TheOddsAPIAdapter
from app.domain.time_utils import now_utc
from app.infra.providers import infrastructure
from app.infra.repositories import SportRepository, LeagueRepository
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

    api_adapter = TheOddsAPIAdapter(
        api_key=settings.odds_api_key,
        base_url=settings.odds_api_base_url,
        regions=settings.odds_api_regions,
        markets=settings.odds_api_markets,
    )

    try:
        # Use shared infrastructure session factory
        async with infrastructure.session_factory() as session:
            sport_repo = SportRepository(session)
            league_repo = LeagueRepository(session)
            normalizer = OddsNormalizer(session)

            sport_id = await sport_repo.get_or_create("football", "Football (Soccer)")

            total_processed = 0

            for league_key in settings.odds_api_leagues:
                logger.info("collecting_league", league=league_key)

                league_id = await league_repo.get_or_create(
                    sport_id=sport_id,
                    key=league_key,
                    name=league_key.replace("_", " ").title(),
                    region="eu",
                )

                odds_data = await api_adapter.get_odds(
                    sport=league_key,
                    regions=settings.odds_api_regions,
                    markets=settings.odds_api_markets,
                )

                events_processed = 0
                for event_data in odds_data:
                    event_id = await normalizer.process_event_data(event_data, sport_id, league_id)
                    if event_id:
                        events_processed += 1

                logger.info("league_processed", league=league_key, events_count=events_processed)
                events_processed_total.inc(events_processed)
                total_processed += events_processed

            await session.commit()

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
