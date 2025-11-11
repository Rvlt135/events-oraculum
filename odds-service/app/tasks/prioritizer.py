"""
Prioritizer tasks for event prioritization.
"""
from typing import Dict
import structlog

from app.config import policy_loader
from app.utils.time_utils import now_utc
from app.infrastructure.di.services import get_prioritizer_service
from app.tasks.broker import broker

logger = structlog.get_logger()


@broker.task()
async def prioritize_events(provider_key: str) -> Dict[str, str]:
    """
    Prioritize events for a single competition.

    Args:
        provider_key: Competition provider key

    Returns:
        Task result with metrics
    """
    start_time = now_utc()
    logger.info("prioritize_events_task_started", provider_key=provider_key, timestamp=start_time.isoformat())

    if not hasattr(broker.state, 'container'):
        raise RuntimeError("Container not found in broker.state")

    try:
        prioritizer_service = await get_prioritizer_service()

        providers = policy_loader.get_providers()
        provider = providers[0] if providers else "odds_api"

        metrics = await prioritizer_service.rank(
            provider_key=provider_key,
            provider=provider,
        )

        duration = (now_utc() - start_time).total_seconds()

        logger.info(
            "prioritize_events_task_completed",
            provider_key=provider_key,
            duration_seconds=duration,
            processed=metrics["processed"],
            llm_batches=metrics["llm_batches"],
            errors=metrics["errors"],
            fallback_used=metrics["fallback_used"]
        )

        return {
            "status": "success",
            "provider_key": provider_key,
            "processed": str(metrics["processed"]),
            "llm_batches": str(metrics["llm_batches"]),
            "errors": str(metrics["errors"]),
            "fallback_used": str(metrics["fallback_used"]),
            "duration_seconds": str(duration),
            "timestamp": now_utc().isoformat(),
        }

    except Exception as e:
        logger.error("prioritize_events_task_failed", provider_key=provider_key, error=str(e), exc_info=True)
        return {"status": "error", "provider_key": provider_key, "message": str(e)}


@broker.task()
async def prioritize_all() -> Dict[str, str]:
    """
    Prioritize events for all competitions (single unified task).

    Returns:
        Task result with aggregated metrics
    """
    start_time = now_utc()
    logger.info("prioritize_all_task_started", timestamp=start_time.isoformat())

    if not hasattr(broker.state, 'container'):
        raise RuntimeError("Container not found in broker.state")

    try:
        prioritizer_service = await get_prioritizer_service()

        providers = policy_loader.get_providers()
        provider = providers[0] if providers else "odds_api"

        policy_dict = policy_loader.get_events_policy(provider=provider)
        if not policy_dict:
            logger.warning("policy_not_found_for_provider", provider=provider)
            return {"status": "error", "message": f"Policy not found for provider: {provider}"}

        competitions_free = policy_dict.get("competitions", {}).get("free", [])
        competitions_pro = policy_dict.get("competitions", {}).get("pro", [])
        all_keys = list(set(competitions_free + competitions_pro))

        logger.info("prioritize_all_competitions_loaded", total=len(all_keys))

        total_processed = 0
        total_batches = 0
        total_errors = 0
        fallback_count = 0

        for provider_key in all_keys:
            try:
                metrics = await prioritizer_service.rank(
                    provider_key=provider_key,
                    provider=provider,
                )

                total_processed += metrics["processed"]
                total_batches += metrics["llm_batches"]
                total_errors += metrics["errors"]
                if metrics["fallback_used"]:
                    fallback_count += 1

            except Exception as e:
                logger.error("prioritize_all_competition_failed", provider_key=provider_key, error=str(e))
                total_errors += 1

        duration = (now_utc() - start_time).total_seconds()

        logger.info(
            "prioritize_all_task_completed",
            duration_seconds=duration,
            competitions=len(all_keys),
            total_processed=total_processed,
            total_batches=total_batches,
            total_errors=total_errors,
            fallback_count=fallback_count
        )

        return {
            "status": "success",
            "competitions": str(len(all_keys)),
            "total_processed": str(total_processed),
            "total_batches": str(total_batches),
            "total_errors": str(total_errors),
            "fallback_count": str(fallback_count),
            "duration_seconds": str(duration),
            "timestamp": now_utc().isoformat(),
        }

    except Exception as e:
        logger.error("prioritize_all_task_failed", error=str(e), exc_info=True)
        return {"status": "error", "message": str(e)}


async def enqueue_prioritization_after_collect(collect_result: Dict[str, str]) -> None:
    """
    Enqueue prioritization tasks after successful collection.

    Args:
        collect_result: Result dict from collect_events task
    """
    if collect_result.get("status") != "success":
        logger.info("collect_events_not_successful_skipping_prioritization", result=collect_result)
        return

    logger.info("collect_events_successful_enqueueing_prioritization")

    providers = policy_loader.get_providers()
    provider = providers[0] if providers else "odds_api"

    policy_dict = policy_loader.get_events_policy(provider=provider)
    if not policy_dict:
        logger.warning("policy_not_found_cannot_enqueue_prioritization", provider=provider)
        return

    prioritizer_config = policy_dict.get("prioritizer", {})
    enabled = prioritizer_config.get("enabled", True)
    mode = prioritizer_config.get("mode", "per_competition")

    if not enabled:
        logger.info("prioritization_disabled_in_policy")
        return

    if mode == "all":
        task = await prioritize_all.kiq()
        logger.info("prioritize_all_enqueued", task_id=task.task_id, job="prioritize_all")

    elif mode == "per_competition":
        competitions_free = policy_dict.get("competitions", {}).get("free", [])
        competitions_pro = policy_dict.get("competitions", {}).get("pro", [])
        all_keys = list(set(competitions_free + competitions_pro))

        logger.info("enqueueing_per_competition_prioritization", total_competitions=len(all_keys))

        enqueued_keys = set()
        task_ids = []

        for provider_key in all_keys:
            if provider_key in enqueued_keys:
                logger.debug("provider_key_already_enqueued_skipping", provider_key=provider_key)
                continue

            try:
                task = await prioritize_events.kiq(provider_key=provider_key)
                enqueued_keys.add(provider_key)
                task_ids.append(task.task_id)

                logger.info(
                    "prioritize_events_enqueued",
                    provider_key=provider_key,
                    task_id=task.task_id,
                    job="prioritize_events"
                )

            except Exception as e:
                logger.error("failed_to_enqueue_prioritization", provider_key=provider_key, error=str(e))

        logger.info(
            "per_competition_prioritization_enqueued",
            total_competitions=len(all_keys),
            enqueued=len(enqueued_keys),
            task_ids=task_ids
        )

    else:
        logger.warning("unknown_prioritization_mode", mode=mode)
