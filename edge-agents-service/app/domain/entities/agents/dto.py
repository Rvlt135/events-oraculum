from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal

from app.domain.entities.collector_api.event_layer_dto import EventFeatureBundleDTO, EventEdgeDTO


class AgentInputDTO(BaseModel):
    event_id: UUID
    competition_id: UUID
    season: int

    match_date: datetime

    bundle: EventFeatureBundleDTO
    edge: EventEdgeDTO

class AgentOutputDTO(BaseModel):
    agent_name: str
    event_id: UUID

    score: Optional[float] = None          # Основной результат (если нужен)
    signals: Optional[List[str]] = None    # Список выводов
    raw: Optional[Dict[str, Any]] = None   # Что угодно, что агент хочет вернуть


class MainAnalysisOutputDTO(BaseModel):
    event_id: UUID
    competition_id: UUID
    season: int
    match_date: datetime

    # итоговая метрика по событию
    aggregated_score: float

    # краткое текстовое резюме (агрегатор формирует)
    summary: str

    decision: Literal["home_win", "draw", "away_win", "no_bet"]
    decision_team_id: UUID | None

    # результаты всех агентов
    agents_outputs: Dict[str, AgentOutputDTO]