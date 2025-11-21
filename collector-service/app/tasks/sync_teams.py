"""
Task for syncing teams from API Football.
"""
from typing import Dict
import structlog

from app.tasks.broker import broker
from app.infrastructure.di.services import get_teams_sync_service

logger = structlog.get_logger()


@broker.task()
async def sync_teams_from_api_football(provider: str = "odds_api") -> Dict[str, str]:
    """
    Sync teams from API Football for all configured competitions.

    This task fetches team data from API Football for each competition
    configured in provider_policy.yml with api_football section.

    Uses team_slug as unique identifier to avoid duplicates.
    Upserts teams: creates new or updates external_ids.api_football.team_id.

    Args:
        provider: Provider name (default: "odds_api")

    Returns:
        Dict with status and counts of created/updated/errors
    """
    logger.info("sync_teams_task_started", provider=provider)

    try:
        teams_sync_service = await get_teams_sync_service()

        result = await teams_sync_service.sync_all_teams(provider=provider)

        logger.info(
            "sync_teams_task_completed",
            provider=provider,
            created=result["created"],
            updated=result["updated"],
            errors=result["errors"]
        )

        return {
            "status": "success",
            "created": str(result["created"]),
            "updated": str(result["updated"]),
            "errors": str(result["errors"]),
        }

    except Exception as e:
        logger.error(
            "sync_teams_task_failed",
            provider=provider,
            error=str(e),
            exc_info=True
        )
        return {
            "status": "error",
            "message": str(e),
        }
