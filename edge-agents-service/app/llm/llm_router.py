from app.llm.base import BaseLLMClient


class LLMRouter:
    def __init__(self, client: BaseLLMClient):
        self.client = client

    async def generate(self, prompt: str, schema):
        return await self.client.generate(schema=schema, prompt=prompt)

    def select_client(self, model_id: str) -> BaseLLMClient:
        pass

