import asyncio
from datetime import datetime

from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import RedisAsyncResultBackend, RedisScheduleSource, ListQueueBroker

from services.odds_service.clients import TheOddsAPIClient
from services.odds_service.config import get_odds_service_config
from services.odds_service.repositories import EventsRepository
from services.odds_service.services import OddsNormalizer

config = get_odds_service_config()

redis_backend = RedisAsyncResultBackend(config.redis.redis_url)
broker = ListQueueBroker(url=config.redis.redis_url).with_result_backend(redis_backend)

schedule_source = RedisScheduleSource(config.redis.redis_url)


@broker.task(schedule=[{"cron": "0 */12 * * *"}])
async def collect_odds_task() -> dict[str, str]:
    print(f"[{datetime.utcnow()}] Starting odds collection task...")

    api_client = TheOddsAPIClient(config.odds_api)
    repository = EventsRepository(config.database)
    normalizer = OddsNormalizer(repository)

    try:
        await repository.connect()

        sport_id = await repository.get_or_create_sport("football", "Football (Soccer)")

        for league_key in config.odds_api.odds_api_leagues:
            print(f"Collecting odds for league: {league_key}")

            league_id = await repository.get_or_create_league(
                sport_id=sport_id,
                key=league_key,
                name=league_key.replace("_", " ").title(),
                region="eu",
            )

            odds_data = await api_client.get_odds(
                sport=league_key,
                regions=config.odds_api.odds_api_regions,
                markets=config.odds_api.odds_api_markets,
            )

            events_processed = 0
            for event_data in odds_data:
                event_id = await normalizer.process_event_data(event_data, sport_id, league_id)
                if event_id:
                    events_processed += 1

            print(f"Processed {events_processed} events for {league_key}")

        return {"status": "success", "timestamp": datetime.utcnow().isoformat()}

    except Exception as e:
        print(f"Error in odds collection task: {e}")
        return {"status": "error", "message": str(e)}

    finally:
        await repository.disconnect()
        await api_client.close()


async def start_scheduler() -> None:
    scheduler = TaskiqScheduler(
        broker=broker,
        sources=[schedule_source, LabelScheduleSource(broker)],
    )

    await scheduler.startup()
    print("TaskIQ scheduler started successfully")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down scheduler...")
        await scheduler.shutdown()
