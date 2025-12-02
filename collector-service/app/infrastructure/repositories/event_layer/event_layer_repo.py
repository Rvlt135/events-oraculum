from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.event_layer.dto import EventFeatureBundleDTO, EventEdgeDTO
from app.infrastructure.db.orm.event_leayer.event_feature_bundle import EventFeatureBundleORM
from app.infrastructure.db.orm.event_leayer.event_edge import EventEdgeORM
from app.infrastructure.repositories.base import BaseRepository

logger = structlog.get_logger()


class EventLayerRepository(BaseRepository[EventFeatureBundleORM]):
    def __init__(self, session: AsyncSession):
        super().__init__(EventFeatureBundleORM, session)

    async def store_bundle(
        self,
        bundle: EventFeatureBundleDTO,
        competition_id: UUID,
        season: int,
    ) -> EventFeatureBundleORM:
        """Store event feature bundle with upsert behavior.
        
        Args:
            bundle: Event feature bundle DTO to store.
            competition_id: Competition identifier.
            season: Season year.
            
        Returns:
            EventFeatureBundleORM instance (created or updated).
        """
        logger.debug(
            "store_bundle_called",
            event_id=str(bundle.event_id),
            competition_id=str(competition_id),
            season=season,
        )
        
        # Serialize DTO with nested event_id fields removed
        payload = bundle.to_clean_dict()
        
        # Upsert using ON CONFLICT DO UPDATE
        stmt = insert(EventFeatureBundleORM).values(
            event_id=bundle.event_id,
            competition_id=competition_id,
            season=season,
            bundle_json=payload,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[EventFeatureBundleORM.event_id],
            set_={
                "competition_id": stmt.excluded.competition_id,
                "season": stmt.excluded.season,
                "bundle_json": stmt.excluded.bundle_json,
            }
        )
        stmt = stmt.returning(EventFeatureBundleORM)
        
        result = await self.session.execute(stmt)
        obj = result.scalar_one()
        await self.session.flush()
        await self.session.refresh(obj)
        
        logger.debug(
            "store_bundle_completed",
            event_id=str(bundle.event_id),
            competition_id=str(competition_id),
            season=season,
        )
        
        return obj

    async def store_bundles(
        self,
        bundles: list[EventFeatureBundleDTO],
        competition_id: UUID,
        season: int,
    ) -> int:
        """Bulk store event feature bundles.
        
        Args:
            bundles: List of event feature bundle DTOs to store.
            competition_id: Competition identifier.
            season: Season year.
            
        Returns:
            Number of successfully stored bundles.
        """
        logger.debug(
            "store_bundles_called",
            count=len(bundles),
            competition_id=str(competition_id),
            season=season,
        )
        
        if not bundles:
            return 0
        
        # Validate uniqueness by event_id
        event_ids = [bundle.event_id for bundle in bundles]
        existing_result = await self.session.execute(
            select(EventFeatureBundleORM.event_id).where(
                EventFeatureBundleORM.event_id.in_(event_ids)
            )
        )
        existing_event_ids = set(existing_result.scalars().all())
        
        # Filter out existing bundles
        new_bundles = [b for b in bundles if b.event_id not in existing_event_ids]
        
        if existing_event_ids:
            logger.debug(
                "store_bundles_duplicates_filtered",
                existing_count=len(existing_event_ids),
                new_count=len(new_bundles),
            )
        
        if not new_bundles:
            logger.debug("store_bundles_no_new_bundles")
            return 0
        
        # Create ORM objects with cleaned bundle_json
        orm_objects = [
            EventFeatureBundleORM(
                event_id=bundle.event_id,
                competition_id=competition_id,
                season=season,
                bundle_json=bundle.to_clean_dict(),
            )
            for bundle in new_bundles
        ]
        
        logger.debug("store_bundles_orm_objects_created", count=len(orm_objects))
        
        # Bulk insert
        self.session.add_all(orm_objects)
        await self.session.flush()
        await self.session.commit()
        
        logger.debug(
            "store_bundles_completed",
            stored=len(orm_objects),
            competition_id=str(competition_id),
            season=season,
        )
        
        return len(orm_objects)

    async def get_bundles(self, event_ids: list[UUID]) -> list[EventFeatureBundleORM]:
        """Fetch event feature bundles by event IDs.
        
        Args:
            event_ids: List of event UUIDs to fetch bundles for.
            
        Returns:
            List of EventFeatureBundleORM instances, ordered by event_id ASC.
        """
        logger.debug("get_bundles_called", event_ids_count=len(event_ids))
        
        if not event_ids:
            return []
        
        stmt = (
            select(EventFeatureBundleORM)
            .where(EventFeatureBundleORM.event_id.in_(event_ids))
            .order_by(EventFeatureBundleORM.event_id.asc())
        )
        
        result = await self.session.execute(stmt)
        bundles = list(result.scalars().all())
        
        logger.debug("get_bundles_completed", fetched_count=len(bundles))
        
        return bundles

    async def store_edges(
        self,
        items: list[EventEdgeDTO],
        competition_id: UUID,
        season: int,
    ) -> int:
        """Bulk store event edges.
        
        Args:
            items: List of EventEdgeDTO instances to store.
            competition_id: Competition identifier.
            season: Season year.
            
        Returns:
            Number of successfully stored edges.
        """
        logger.debug(
            "store_edges_called",
            count=len(items),
            competition_id=str(competition_id),
            season=season,
        )
        
        if not items:
            return 0
        
        # Create ORM objects with serialized edges_json
        orm_objects = [
            EventEdgeORM(
                event_id=item.event_id,
                competition_id=competition_id,
                season=season,
                edges_json=item.model_dump(mode="json"),
            )
            for item in items
        ]
        
        logger.debug("store_edges_orm_objects_created", count=len(orm_objects))
        
        # Bulk insert
        self.session.add_all(orm_objects)
        await self.session.flush()
        await self.session.commit()
        
        logger.debug(
            "edges_stored",
            count=len(orm_objects),
            competition_id=str(competition_id),
            season=season,
        )
        
        return len(orm_objects)