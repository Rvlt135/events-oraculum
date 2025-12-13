# from typing import List, Optional
# from datetime import datetime
# from fastapi import APIRouter, BackgroundTasks, Query
# from pydantic import BaseModel
# import structlog
#
# # from app.tasks.run_batch import run_batch_task
#
# router = APIRouter(prefix="/_agents", tags=["Run"])
#
# logger = structlog.get_logger()
#
#
# class RunBatchRequest(BaseModel):
#     event_ids: Optional[List[str]] = None
#     league: Optional[str] = None
#     from_date: Optional[str] = None
#     to_date: Optional[str] = None
#     prompt_template: str = "betting_analysis"
#
#
# @router.post("/run_batch")
# async def run_batch(request: RunBatchRequest) -> dict:
#     logger.info(
#         "run_batch_request",
#         event_ids_count=len(request.event_ids) if request.event_ids else 0,
#         league=request.league,
#         prompt_template=request.prompt_template
#     )
#
#     # task = await run_batch_task.kiq(
#     #     event_ids=request.event_ids,
#     #     league=request.league,
#     #     from_date=request.from_date,
#     #     to_date=request.to_date,
#     #     prompt_template=request.prompt_template
#     # )
#
#     return {
#         "status": "enqueued",
#         "message": "Batch analysis task has been queued",
#         # "job_id": str(task.task_id),
#         "timestamp": datetime.utcnow().isoformat()
#     }
