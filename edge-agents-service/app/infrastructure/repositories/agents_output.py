from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import select, and_, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.domain.entities.recommendation import RecommendationResponse, RecommendationCreate
from app.domain.entities.agents.dto import AgentOutputDTO
from app.infrastructure.db.orm.recommendation import RecommendationORM
from app.infrastructure.db.orm.agent_analysis_outputs import AgentAnalysisOutputsORM

logger = structlog.get_logger()


class AgentsOutputRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_agent_analysis_outputs(
        self,
        event_id: UUID,
        outputs: Dict[str, AgentOutputDTO]
    ) -> None:
        """
        Upsert agent analysis outputs for an event.
        
        Args:
            event_id: UUID of the event
            outputs: Dictionary mapping agent names to their output DTOs
        """
        # Extract upsert payload
        outputs_json: Dict[str, Any] = {
            agent_name: output.model_dump(mode="json") 
            for agent_name, output in outputs.items()
        }
        
        main_output = outputs.get("main")
        if not main_output:
            raise ValueError("Missing 'main' output in outputs dict")
        
        main_score: float = main_output.score
        if main_score is None:
            raise ValueError("main output score is None")
        
        # Get decision from main output (decision or summary field)
        decision: Optional[str] = getattr(main_output, "decision", None) or getattr(main_output, "summary", None)
        
        # Execute SQLAlchemy insert with on_conflict_do_update
        insert_stmt = insert(AgentAnalysisOutputsORM).values(
            event_id=event_id,
            outputs_json=outputs_json,
            main_score=main_score,
            decision=decision,
            updated_at=func.now(),
        )
        
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=["event_id"],
            set_={
                "outputs_json": insert_stmt.excluded.outputs_json,
                "main_score": insert_stmt.excluded.main_score,
                "decision": insert_stmt.excluded.decision,
                "updated_at": func.now(),
            }
        )
        
        await self.session.execute(stmt)
        await self.session.commit()
        
        logger.debug(
            "upsert_agent_analysis_outputs",
            event_id=str(event_id),
            main_score=main_score,
        )