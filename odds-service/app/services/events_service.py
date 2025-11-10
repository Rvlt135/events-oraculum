"""
Events service for managing event collection targets.
"""
from typing import Literal, List
import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.domain.entities.events_targets import EventsTargetsDTO, FilteredReasonDTO
from app.infrastructure.repositories.competitions import CompetitionsRepository
from app.config import policy_loader

logger = structlog.get_logger()


class EventsService:
    """Service for managing event collection targets and validation."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def select_target_competitions(
        self, plan: Literal["free", "pro", "all"] = "all"
    ) -> EventsTargetsDTO:
        """
        Select target competitions for event collection based on policy and DB validation.

        This method:
        1. Loads competition whitelist from policy (free/pro/all)
        2. Validates each competition against DB (exists + is_active)
        3. Filters out invalid competitions with reasons
        4. Creates deterministic batches for processing

        Args:
            plan: Plan filter - 'free' (only free tier), 'pro' (free + pro), 'all' (free + pro)

        Returns:
            EventsTargetsDTO with validated competitions batched for processing
        """
        logger.info("select_target_competitions_started", plan=plan)

        # Step 1: Load whitelist from policy
        provider = "odds_api"
        whitelist = policy_loader.get_competitions_whitelist(provider, plan)
        total_in_policy = len(whitelist)

        logger.info("whitelist_loaded_from_policy", plan=plan, total=total_in_policy)

        if not whitelist:
            logger.warning("empty_whitelist", plan=plan)
            return EventsTargetsDTO(
                provider=provider,
                plan=plan,
                total_in_policy=0,
                total_valid=0,
                filtered_out=[],
                batches=[],
            )

        # Step 2: Validate against DB
        valid_keys, filtered_out = await self._validate_competitions(whitelist)

        logger.info(
            "competitions_validated",
            plan=plan,
            total_in_policy=total_in_policy,
            valid=len(valid_keys),
            filtered=len(filtered_out),
        )

        # Step 3: Create batches
        batch_size = policy_loader.get_batch_size_competitions(provider, default=10)
        batches = self._create_batches(valid_keys, batch_size)

        logger.info(
            "target_competitions_selected",
            plan=plan,
            total_batches=len(batches),
            batch_size=batch_size,
        )

        return EventsTargetsDTO(
            provider=provider,
            plan=plan,
            total_in_policy=total_in_policy,
            total_valid=len(valid_keys),
            filtered_out=filtered_out,
            batches=batches,
        )

    async def _validate_competitions(
        self, provider_keys: List[str]
    ) -> tuple[List[str], List[FilteredReasonDTO]]:
        """
        Validate competitions against DB.

        Args:
            provider_keys: List of competition provider_keys to validate

        Returns:
            Tuple of (valid_keys, filtered_out_with_reasons)
        """
        valid_keys = []
        filtered_out = []

        async with self._session_factory() as session:
            comp_repo = CompetitionsRepository(session)

            for provider_key in provider_keys:
                try:
                    # Get competition from DB
                    competition = await comp_repo.get_by_provider_key(
                        provider="odds_api", provider_key=provider_key
                    )

                    if not competition:
                        logger.debug(
                            "competition_not_found_in_db", provider_key=provider_key
                        )
                        filtered_out.append(
                            FilteredReasonDTO(
                                provider_key=provider_key, reason="not_found"
                            )
                        )
                        continue

                    if not competition.is_active:
                        logger.debug(
                            "competition_inactive", provider_key=provider_key
                        )
                        filtered_out.append(
                            FilteredReasonDTO(
                                provider_key=provider_key, reason="inactive"
                            )
                        )
                        continue

                    # Valid competition
                    valid_keys.append(provider_key)
                    logger.debug(
                        "competition_validated", provider_key=provider_key
                    )

                except Exception as e:
                    logger.error(
                        "competition_validation_error",
                        provider_key=provider_key,
                        error=str(e),
                    )
                    filtered_out.append(
                        FilteredReasonDTO(provider_key=provider_key, reason="not_found")
                    )

        return valid_keys, filtered_out

    def _create_batches(self, items: List[str], batch_size: int) -> List[List[str]]:
        """
        Create deterministic batches from list of items.

        Args:
            items: List of items to batch (already sorted)
            batch_size: Size of each batch

        Returns:
            List of batches
        """
        if not items or batch_size <= 0:
            return []

        batches = []
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            batches.append(batch)

        logger.debug("batches_created", total_items=len(items), batch_size=batch_size, total_batches=len(batches))
        return batches
