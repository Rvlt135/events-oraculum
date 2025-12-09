"""
Builder for building data layer features
"""

import structlog
from uuid import UUID, uuid4
from typing import Optional

from app.domain.entities import CompetitionEntity
from app.domain.entities.data_layer.sport_dto import SportDTO
from app.domain.entities.odds_api.dto import SportList
from app.infrastructure.config.policy_loader import PolicyLoader

logger = structlog.get_logger()


class DataLayerBuilder:
    """Builder for data layer sports, competitions, events"""

    def __init__(self, policy_loader: Optional[PolicyLoader] = None):
        """
        Initialize DataLayerBuilder.
        
        Args:
            policy_loader: Optional PolicyLoader for accessing API Football config
        """
        self.policy_loader = policy_loader

    def normalize_sports(self, sport_list: SportList, visibility_map: dict[str, str]) -> list[SportDTO]:
        """
        Normalize raw sports data into unique SportDTO list.

        Applies legacy category normalization and assigns visibility from map.
        Ensures uniqueness by normalized category (group).

        Args:
            sport_list: SportList containing raw sports from provider
            visibility_map: Dict mapping normalized category to visibility ("free", "pro", "unavailable")

        Returns:
            List of unique SportDTO (empty list on error or if input is empty)
        """
        logger.debug("normalize_sports_started", raw_count=len(sport_list.sports) if sport_list.sports else 0)

        try:
            # Validate input
            if not sport_list.sports:
                logger.debug("normalize_sports_empty_input")
                return []

            results: list[SportDTO] = []
            seen: set[str] = set()

            for sport in sport_list.sports:
                # Normalize category using legacy logic (same as sync_sports_categories)
                group = sport.group.lower().strip()
                if not group:
                    continue

                # Normalize: replace spaces with underscores
                category = group.replace(" ", "_")

                # Skip duplicates by normalized category
                if category in seen:
                    continue
                seen.add(category)

                # Get plan visibility from map (default to "unavailable")
                plan_visibility = visibility_map.get(category, "unavailable")

                # Compute is_active
                is_active = sport.active

                # Build DTO
                dto = SportDTO(
                    provider="odds_api",
                    category=category,
                    is_active=is_active,
                    plan_visibility=plan_visibility,
                )
                results.append(dto)
                
                logger.debug(
                    "normalize_sports_item",
                    category=category,
                    visibility=plan_visibility,
                    is_active=is_active,
                )

            logger.info("normalize_sports_completed", count=len(results))
            return results

        except Exception as e:
            logger.error("normalize_sports_failed", error=str(e), exc_info=True)
            return []

    def normalize_competitions(self, sport_list: SportList, visibility_map: dict[str, str]) -> list[CompetitionEntity]:
        """
        Normalize raw sports data into CompetitionEntity list.
        
        Creates partial CompetitionEntity instances (without id and sport_id)
        from each sport in the list. Populates api_sources from API Football config if available.
        
        Args:
            sport_list: SportList containing raw sports from provider
            visibility_map: Dict mapping slug_key to visibility ("free", "pro", "unavailable")
            
        Returns:
            List of CompetitionEntity (partial, without id and sport_id)
        """
        logger.debug("normalize_competitions_started", raw_count=len(sport_list.sports) if sport_list.sports else 0)
        
        try:
            # Validate input
            if not sport_list.sports:
                logger.debug("normalize_competitions_empty_input")
                return []
            
            # Load API Football config before loop
            api_football = self.policy_loader.get_api_football("odds_api") if self.policy_loader else None
            api_competitions = api_football.competitions if api_football else {}
            
            results: list[CompetitionEntity] = []
            
            for sport in sport_list.sports:
                # Use sport.key directly as slug_key
                slug_key = sport.key
                
                # Normalize category from sport.group (same normalization as normalize_sports)
                group = sport.group.lower().strip()
                # Normalize: replace spaces with underscores
                category = group.replace(" ", "_") if group else ""
                
                # Get plan visibility from map (default to "unavailable")
                plan_visibility = visibility_map.get(slug_key, "unavailable")
                
                # Compute is_active
                is_active = sport.active
                
                # Determine api_sources
                api_src = api_competitions.get(slug_key)
                api_sources = api_src.model_dump() if api_src else {}
                
                # Build partial entity (without id and sport_id)
                # Use placeholder UUIDs since they're required but won't be used
                entity = CompetitionEntity.model_construct(
                    id=uuid4(),  # Placeholder, will be set later
                    sport_id=uuid4(),  # Placeholder, will be set later
                    provider="odds_api",
                    description=sport.description,
                    slug_key=slug_key,
                    title=sport.title,
                    category=category,
                    plan_visibility=plan_visibility,
                    is_active=is_active,
                    api_sources=api_sources,
                )
                results.append(entity)
                
                logger.debug(
                    "normalize_competition_item",
                    slug_key=slug_key,
                    category=category,
                    visibility=plan_visibility,
                    is_active=is_active,
                )
                
                logger.debug(
                    "competition_api_source_resolved",
                    slug_key=slug_key,
                    has_api=bool(api_sources),
                )
            
            logger.info("normalize_competitions_completed", count=len(results))
            return results
            
        except Exception as e:
            logger.error("normalize_competitions_failed", error=str(e), exc_info=True)
            return []