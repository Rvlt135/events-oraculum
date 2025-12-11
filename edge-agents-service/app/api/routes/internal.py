from typing import Dict
from fastapi import APIRouter
import structlog

from app.prompts.processor import PromptProcessor

logger = structlog.get_logger()

router = APIRouter(prefix="/_agents", tags=["Agents"])

# TODO: duplicate from health.py
# @router.get("/health")
# async def health() -> dict:
#     return {"status": "healthy", "service": "edge-agents-service"}

# TODO: duplicate from run.py
# @router.post("/run_batch")
# async def run_batch(
#     background_tasks: BackgroundTasks,
#     event_ids: Optional[List[UUID]] = None,
#     league: Optional[str] = None,
#     from_date: Optional[datetime] = None,
#     to_date: Optional[datetime] = None,
#     prompt_template: str = Query(default="betting_analysis"),
#     session: AsyncSession = Depends(get_session),
# ) -> dict:
#     logger.info(
#         "run_batch_requested",
#         event_ids_count=len(event_ids) if event_ids else 0,
#         league=league,
#         prompt_template=prompt_template,
#     )
#
#     repository = RecommendationRepository(session)
#     runner = AgentRunner(repository, prompt_template=prompt_template)
#
#     result = await runner.run_batch(
#         event_ids=event_ids,
#         league=league,
#         from_date=from_date,
#         to_date=to_date,
#     )
#
#     return result

# TODO: duplicate from recommendations.py
# @router.get("/recommendations", response_model=List[RecommendationResponse])
# async def get_recommendations(
#     league: Optional[str] = Query(default=None),
#     from_date: Optional[datetime] = Query(default=None, alias="from"),
#     to_date: Optional[datetime] = Query(default=None, alias="to"),
#     min_conf: Optional[float] = Query(default=None, ge=0.0, le=1.0),
#     limit: int = Query(default=100, ge=1, le=1000),
#     session: AsyncSession = Depends(get_session),
# ) -> List[RecommendationResponse]:
#     logger.info(
#         "get_recommendations_requested",
#         league=league,
#         from_date=from_date,
#         to_date=to_date,
#         min_conf=min_conf,
#         limit=limit,
#     )
#
#     repository = RecommendationRepository(session)
#
#     recommendations = await repository.get_recommendations(
#         league=league,
#         from_date=from_date,
#         to_date=to_date,
#         min_confidence=min_conf,
#         limit=limit,
#     )
#
#     logger.info("recommendations_returned", count=len(recommendations))
#
#     return recommendations


@router.get("/prompts")
async def list_prompts() -> Dict[str, str]:
    processor = PromptProcessor(prompts_dir="prompts")
    templates = processor.list_available_templates()

    logger.info("prompts_listed", count=len(templates))

    return templates


@router.post("/prompts/reload")
async def reload_prompts() -> dict:
    processor = PromptProcessor(prompts_dir="prompts")
    processor.reload_templates()

    logger.info("prompts_reloaded")

    return {"status": "success", "message": "Prompts reloaded"}
