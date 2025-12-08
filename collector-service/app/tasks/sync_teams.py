"""
Task for syncing teams from API Football.
"""
from typing import Dict
import structlog

from app.infrastructure.di.container import Container
from app.infrastructure.di.factory import create_teams_sync_service
from app.tasks.broker import broker

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
        container: "Container" = broker.state.container
        teams_sync_service = create_teams_sync_service(container)

        api_football_config = teams_sync_service.policy_loader.get_api_football(provider)

        competitions = await teams_sync_service.get_competitions_for_sync(provider, api_football_config.competitions)

        if not competitions:
            logger.warning("no_competitions_for_sync", provider=provider)
            return {"status": "not_found_competitions", "created": 0, "updated": 0, "errors": 0}

        result = await teams_sync_service.sync_all_teams(provider=provider, competitions=competitions)

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
