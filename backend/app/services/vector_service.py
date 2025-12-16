from app.core.llm import NeuroVaultLLM
from app.config import settings

class VectorService:
    @classmethod
    async def embed_text(cls, text: str) -> list[float]:
        """
        Generate embeddings using Ollama (Async).
        """
        try:
            response = await NeuroVaultLLM.embed(model=settings.EMBEDDING_MODEL, input_text=text)
            return response["embedding"]
        except Exception as e:
            print(f"Ollama embedding failed: {e}")
            raise e
