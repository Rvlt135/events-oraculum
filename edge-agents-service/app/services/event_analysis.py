"""
Service for building team features
"""
from typing import Dict, Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.entities.agents.dto import AgentInputDTO
from app.domain.entities.collector_api.dto import CompetitionReadDTO, UpcomingEventCatalogDTO
from app.domain.entities.collector_api.event_layer_dto import EventFeatureBundleDTO, EventEdgeDTO
from app.infrastructure.cache.catalog.halper import CatalogHalperCache
from app.infrastructure.http.collector_api_client import CollectorApiClient
from app.pipelines.agents_pipeline import AgentsPipeline

logger = structlog.get_logger()


class EventAnalysisService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        catalog_rdb_halper: CatalogHalperCache,
        agents_pipeline: AgentsPipeline,
    ):
        self.session_factory = session_factory
        self.catalog_rdb_halper = catalog_rdb_halper
        self.agents_pipeline = agents_pipeline