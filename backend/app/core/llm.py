import ollama
from ollama import AsyncClient
from app.config import settings

class NeuroVaultLLM:
    """
    Centralized LLM Wrapper.
    Currently defaults to Ollama, but designed to bridge to LiteLLM or others.
    """
    
    @staticmethod
    async def chat(model: str, messages: list, format: str | dict = None, stream: bool = False, options: dict = None):
        """
        Standard Chat Completion.
        Supports:
        - Stream=True (Yields tokens)
        - Format='json' OR Pydantic Schema / JSON Schema (Structured Outputs)
        - Images in messages
        """
        if settings.LLM_PROVIDER == "ollama":
            # Use AsyncClient for non-blocking IO
            client = AsyncClient(host=settings.LLM_API_BASE)
            try:
                response = await client.chat(
                    model=model, 
                    messages=messages, 
                    format=format, 
                    stream=stream, 
                    options=options
                )
                return response
            except Exception as e:
                print(f"LLM Chat Failed ({model}): {e}")
                raise e
        else:
            raise NotImplementedError(f"Provider {settings.LLM_PROVIDER} not implemented yet.")
    
    @staticmethod
    async def generate(model: str, prompt: str, stream: bool = False):
        """
        Text Completion (Legacy/Simple).
        """
        if settings.LLM_PROVIDER == "ollama":
            client = AsyncClient(host=settings.LLM_API_BASE)
            try:
                response = await client.generate(model=model, prompt=prompt, stream=stream)
                return response
            except Exception as e:
                print(f"LLM Generate Failed ({model}): {e}")
                raise e
        else:
             raise NotImplementedError(f"Provider {settings.LLM_PROVIDER} not implemented yet.")

    @staticmethod
    async def embed(model: str, input_text: str):
        """
        Embedding Generation.
        """
        if settings.LLM_PROVIDER == "ollama":
            client = AsyncClient(host=settings.LLM_API_BASE)
            try:
                response = await client.embeddings(model=model, prompt=input_text)
                return response
            except Exception as e:
                print(f"LLM Embed Failed ({model}): {e}")
                raise e
        else:
             raise NotImplementedError(f"Provider {settings.LLM_PROVIDER} not implemented yet.")
