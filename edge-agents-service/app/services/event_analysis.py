"""
Service for building team features
"""
from typing import Dict, Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.entities.agents.dto import AgentInputDTO, MainAnalysisOutputDTO
from app.domain.entities.collector_api.dto import CompetitionReadDTO, UpcomingEventCatalogDTO
from app.domain.entities.collector_api.event_layer_dto import EventFeatureBundleDTO, EventEdgeDTO
from app.infrastructure.cache.catalog.halper import CatalogHalperCache
from app.infrastructure.cache.events.event_analysis import EventAnalysisCache
from app.infrastructure.http.collector_api_client import CollectorApiClient
from app.infrastructure.repositories.agents_output import AgentsOutputRepository
from app.pipelines.agents_pipeline import AgentsPipeline

logger = structlog.get_logger()


class EventAnalysisService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        cache: EventAnalysisCache,
    ):
        self.session_factory = session_factory
        self._cache = cache

    async def save_agent_analysis_outputs(
        self,
        event_id: UUID,
        main_output: MainAnalysisOutputDTO,
    ) -> None:
        """
        Save agent analysis outputs to database and cache.
        
        Args:
            event_id: UUID of the event
            main_output: MainAnalysisOutputDTO containing aggregated analysis results
        """
        # Save to database
        async with self.session_factory() as session:
            repo = AgentsOutputRepository(session)
            await repo.upsert_agent_analysis_outputs(
                event_id=event_id,
                main_output=main_output,
            )
        
        # Save to cache after DB commit
        await self._cache.save_event_analysis(
            event_id=event_id,
            main_output=main_output,
        )
        
        logger.debug(
            "save_agent_analysis_outputs",
            event_id=str(event_id),
            main_score=main_output.aggregated_score,
            agents_count=len(main_output.agents_outputs),
        )