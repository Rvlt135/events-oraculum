# app/agents/math_agent.py
from app.agents.base import BaseAgent
from app.domain.entities.agents.dto import AgentInputDTO, AgentOutputDTO

class MathAgent(BaseAgent):
    name = "math_agent"

    async def analyze(self, input_data: AgentInputDTO) -> AgentOutputDTO:
        poisson = input_data.bundle.poisson_event_features
        edge = input_data.edge

        # примитивный пример детерминированного скора
        score = float(poisson.lambda_home - poisson.lambda_away)

        return AgentOutputDTO(
            agent_name=self.name,
            event_id=input_data.event_id,
            score=score,
            signals=[
                f"lambda_home={poisson.lambda_home}",
                f"lambda_away={poisson.lambda_away}",
                f"edge_home={edge.edge_home}",
                f"edge_away={edge.edge_away}",
            ],
            raw={
                "lambda_home": poisson.lambda_home,
                "lambda_away": poisson.lambda_away,
                "edge_home": edge.edge_home,
                "edge_away": edge.edge_away,
            },
        )
