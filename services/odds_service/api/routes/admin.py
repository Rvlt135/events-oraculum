from typing import Any

from fastapi import APIRouter, BackgroundTasks

from services.odds_service.tasks import collect_odds_task

router = APIRouter()


@router.post("/trigger-collection")
async def trigger_collection(background_tasks: BackgroundTasks) -> dict[str, str]:
    background_tasks.add_task(collect_odds_task)
    return {"status": "Collection task triggered", "message": "Task running in background"}


@router.get("/stats")
async def get_stats() -> dict[str, Any]:
    return {
        "message": "Statistics endpoint - to be implemented",
        "total_events": 0,
        "total_snapshots": 0,
    }
