from fastapi import APIRouter

from services.odds_service.clients import TheOddsAPIClient
from services.odds_service.config import get_odds_service_config

router = APIRouter()
config = get_odds_service_config()


@router.get("")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/odds-api")
async def odds_api_health() -> dict[str, str | bool]:
    client = TheOddsAPIClient(config.odds_api)
    try:
        is_healthy = await client.health_check()
        return {"status": "healthy" if is_healthy else "unhealthy", "connected": is_healthy}
    finally:
        await client.close()
