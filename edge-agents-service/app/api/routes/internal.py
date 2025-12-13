from typing import Dict
from fastapi import APIRouter, Depends
import structlog

from app.config.security import verify_admin_token
from app.config.settings import settings
from app.prompts.processor import PromptProcessor

logger = structlog.get_logger()

router = APIRouter(prefix="/_agents", tags=["Agents"])

@router.get("/prompts")
async def list_prompts(
        _auth: None = Depends(verify_admin_token)
) -> Dict[str, str]:
    processor = PromptProcessor(prompts_dir=settings.prompts_config_full_path)
    logger.info("prompts_dir", prompts_dir=settings.prompts_config_full_path)
    templates = processor.list_available_templates()

    logger.info("prompts_listed", count=len(templates))

    return templates


@router.post("/prompts/reload")
async def reload_prompts(_auth: None = Depends(verify_admin_token)) -> dict:
    processor = PromptProcessor(prompts_dir="prompts")
    processor.reload_templates()

    logger.info("prompts_reloaded")

    return {"status": "success", "message": "Prompts reloaded"}
