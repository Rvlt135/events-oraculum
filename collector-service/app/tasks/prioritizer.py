"""
Prioritizer tasks for event prioritization.
"""
from typing import Dict
import structlog

from app.utils.time_utils import now_utc
from app.infrastructure.di.services import get_prioritizer_service
from app.tasks.broker import broker
from uuid import uuid4

logger = structlog.get_logger()


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
        container = broker.state.container
        policy_loader = container.policy_loader
        
        providers = policy_loader.get_providers()
        provider = providers[0] if providers else "odds_api"

        events_policy = policy_loader.get_events_policy(provider)
        if not events_policy:
            logger.warning("policy_not_found_for_provider", provider=provider)
            return {"status": "error", "message": f"Policy not found for provider: {provider}"}

        competitions_free = events_policy.competitions.get("free", [])
        competitions_pro = events_policy.competitions.get("pro", [])
        all_keys = list(set(competitions_free + competitions_pro))

        logger.info("prioritize_all_competitions_loaded", total=len(all_keys))

        # Generate unique run_id for idempotency
        run_id = str(uuid4())
        logger.info("prioritize_all_run_id", run_id=run_id)

        # Get model name for QPS limit
        model = prioritizer_service._ai_client.model if prioritizer_service._ai_client else "unknown"

        total_processed = 0
        total_batches = 0
        total_errors = 0
        fallback_count = 0

        for slug_key in all_keys:
            # Idempotency check: skip if already processed in this run
            if await prioritizer_service.tasks_cache.check_idempotency(slug_key, run_id):
                continue

            # Optional: acquire execution lock
            lock_token = await prioritizer_service.tasks_cache.acquire_lock(slug_key)
            if lock_token is None:
                logger.info("lock_not_acquired_skipping", slug_key=slug_key)
                continue

            try:
                # Get events: cache first, then DB fallback
                items = await prioritizer_service.get_upcoming_events_for_slug_key(
                    slug_key=slug_key,
                    provider=provider
                )

                # Skip if no upcoming events
                if not items:
                    logger.info("skip_no_upcoming", slug_key=slug_key)
                    continue

                # Log prioritization start
                logger.info("prioritization_started", slug_key=slug_key, count=len(items))

                # QPS limit check (soft limit)
                await prioritizer_service.tasks_cache.check_qps_limit(model)

                metrics = await prioritizer_service.rank(
                    slug_key=slug_key,
                    provider=provider,
                    events=items,
                )

                # Log prioritization completion
                logger.info(
                    "prioritization_done",
                    slug_key=provider_key,
                    processed=metrics["processed"],
                    llm_batches=metrics["llm_batches"],
                    errors=metrics["errors"],
                    fallback_used=metrics["fallback_used"]
                )

                total_processed += metrics["processed"]
                total_batches += metrics["llm_batches"]
                total_errors += metrics["errors"]
                if metrics["fallback_used"]:
                    fallback_count += 1

            except Exception as e:
                logger.error("prioritize_all_competition_failed", provider_key=provider_key, error=str(e))
                total_errors += 1
            finally:
                # Release lock if acquired
                if lock_token:
                    await prioritizer_service.tasks_cache.release_lock(provider_key, lock_token)

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
    Enqueue prioritization task after successful collection.

    Args:
        collect_result: Result dict from collect_events task
    """
    if collect_result.get("status") != "success":
        logger.info("collect_events_not_successful_skipping_prioritization", result=collect_result)
        return

    logger.info("collect_events_successful_enqueueing_prioritization")

    container = broker.state.container
    policy_loader = container.policy_loader
    
    providers = policy_loader.get_providers()
    provider = providers[0] if providers else "odds_api"

    prioritizer_policy = policy_loader.get_prioritizer_policy(provider)
    if not prioritizer_policy:
        logger.warning("prioritizer_policy_not_found_cannot_enqueue", provider=provider)
        return

    enabled = prioritizer_policy.enabled

    if not enabled:
        logger.info("prioritization_disabled_in_policy")
        return

    task = await prioritize_all.kiq()
    logger.info("prioritize_all_enqueued", task_id=task.task_id)
