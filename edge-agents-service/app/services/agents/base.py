from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel


class AgentPrediction(BaseModel):
    event_id: UUID
    pick: str
    confidence: float
    explanation: str
    model_version: str


class Agent(ABC):
    @abstractmethod
    async def analyze(self, event_features: Dict[str, Any]) -> Optional[AgentPrediction]:
        pass

    @abstractmethod
    def get_model_version(self) -> str:
        pass
