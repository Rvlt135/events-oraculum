from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional
from fastapi import FastAPI, Query, Depends
from fastapi.responses import JSONResponse, ORJSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

from app.config import settings
from app.domain.schemas import (
    ServiceInfoResponse,
    HealthResponse,
    TaskTriggerResponse,
    SnapshotsResponse,
    SnapshotSummary
)
from app.tasks.collector import collect_odds_task
from app.infra.db import db_manager, get_db_session

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("starting_admin_api")
    await db_manager.initialize()
    yield
    await db_manager.dispose()
    logger.info("shutting_down_admin_api")


def create_admin_app(env: str = "development") -> FastAPI:
    app = FastAPI(
        title="Odds Service - Admin API",
        description="Admin API for odds-service management",
        version="0.1.0",
        lifespan=lifespan,
        default_response_class=ORJSONResponse,
    )

    @app.get("/", response_model=ServiceInfoResponse)
    async def root() -> ServiceInfoResponse:
        return ServiceInfoResponse(
            service=f"{settings.service_name}-admin",
            version="0.1.0",
            status="running",
            environment=env,
        )

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="healthy")

    @app.post("/_admin/tasks/collect", response_model=TaskTriggerResponse)
    async def trigger_collection() -> TaskTriggerResponse:
        logger.info("manual_collection_triggered")

        try:
            task = await collect_odds_task.kiq()

            return TaskTriggerResponse(
                status="enqueued",
                message="Collection task enqueued in TaskIQ",
                task_id=str(task.task_id),
            )
        except Exception as e:
            logger.error("failed_to_enqueue_task", error=str(e))
            return TaskTriggerResponse(
                status="error",
                message=f"Failed to enqueue task: {str(e)}",
            )

    @app.get("/_admin/data/snapshots", response_model=SnapshotsResponse)
    async def get_snapshots(
        limit: int = Query(default=100, ge=1, le=1000),
        league: Optional[str] = Query(default=None),
        session: AsyncSession = Depends(get_db_session),
    ) -> SnapshotsResponse:
        logger.info("fetching_snapshots", limit=limit, league=league)

        try:
            from app.infra.repositories import NormalizedOddsRepository

            normalized_repo = NormalizedOddsRepository(session)
            snapshots_data = await normalized_repo.get_normalized_snapshots(
                limit=limit,
                league_key=league
            )

            snapshots = [SnapshotSummary.model_validate(snap) for snap in snapshots_data]

            return SnapshotsResponse(
                count=len(snapshots),
                limit=limit,
                league=league,
                snapshots=snapshots,
            )

        except Exception as e:
            logger.error("failed_to_fetch_snapshots", error=str(e))
            raise

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_admin_app(settings.environment)
