from app.agents.base import BaseAgent
from app.config import settings
from app.core.prompts import Prompts

class MessengerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            model=settings.MESSENGER_MODEL,
            system_prompt=Prompts.MESSENGER_SYSTEM
        )

    async def answer_with_rag(self, query: str, context_chunks: list[str]) -> str:
        # 1. Format context
        formatted_context = "\n---\n".join(context_chunks)
        
        # 2. Generate answer
        prompt = Prompts.MESSENGER_RAG_TEMPLATE.format(query=query)
        return await self.generate(prompt, context=formatted_context)

    async def stream_answer_with_rag(self, query: str, context_chunks: list[str]):
        formatted_context = "\n---\n".join(context_chunks)
        prompt = Prompts.MESSENGER_RAG_TEMPLATE.format(query=query)
        async for token in self.generate_stream(prompt, context=formatted_context):
            yield token
