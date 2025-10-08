from typing import Any

from fastapi import APIRouter, HTTPException

from services.odds_service.config import get_odds_service_config
from services.odds_service.repositories import EventsRepository

router = APIRouter()
config = get_odds_service_config()


@router.get("/upcoming")
async def get_upcoming_events() -> dict[str, Any]:
    repository = EventsRepository(config.database)
    try:
        await repository.connect()

        sport_id_result = await repository.fetch_one(
            "SELECT id FROM sports WHERE name = 'football' LIMIT 1"
        )
        if not sport_id_result:
            raise HTTPException(status_code=404, detail="Sport not found")

        league_id_result = await repository.fetch_one(
            "SELECT id FROM leagues WHERE key = 'soccer_uefa_champs_league' LIMIT 1"
        )
        if not league_id_result:
            raise HTTPException(status_code=404, detail="League not found")

        events = await repository.get_upcoming_events(league_id_result["id"])

        return {"count": len(events), "events": events}

    finally:
        await repository.disconnect()
