from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import select, and_, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.domain.entities.recommendation import RecommendationResponse, RecommendationCreate
from app.domain.entities.agents.dto import AgentOutputDTO, MainAnalysisOutputDTO
from app.infrastructure.db.orm.recommendation import RecommendationORM
from app.infrastructure.db.orm.agent_analysis_outputs import AgentAnalysisOutputsORM

logger = structlog.get_logger()


class AgentsOutputRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_agent_analysis_outputs(
        self,
        event_id: UUID,
        main_output: MainAnalysisOutputDTO
    ) -> None:
        """
        Upsert agent analysis outputs for an event.
        
        Args:
            event_id: UUID of the event
            main_output: MainAnalysisOutputDTO containing aggregated analysis results
        """
        # Extract upsert payload
        outputs_json: Dict[str, Any] = {
            name: dto.model_dump(mode="json") 
            for name, dto in main_output.agents_outputs.items()
        }
        
        main_score: float = main_output.aggregated_score
        decision: str = main_output.summary
        
        # Execute SQLAlchemy insert with on_conflict_do_update
        insert_stmt = insert(AgentAnalysisOutputsORM).values(
            event_id=event_id,
            outputs_json=outputs_json,
            main_score=main_score,
            decision=decision,
        )
        
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=[AgentAnalysisOutputsORM.event_id],
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