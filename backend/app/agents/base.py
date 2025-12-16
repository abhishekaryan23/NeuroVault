from app.core.llm import NeuroVaultLLM
from typing import Optional, List, Dict, Any

class BaseAgent:
    def __init__(self, model: str, system_prompt: str = ""):
        self.model = model
        self.system_prompt = system_prompt

    async def generate(self, user_prompt: str, context: Optional[str] = None) -> str:
        messages = []
        if self.system_prompt:
            messages.append({'role': 'system', 'content': self.system_prompt})
        
        full_prompt = user_prompt
        if context:
            full_prompt += f"\n\nContext:\n{context}"
            
        messages.append({'role': 'user', 'content': full_prompt})

        try:
            response = await NeuroVaultLLM.chat(model=self.model, messages=messages)
            return response['message']['content']
        except Exception as e:
            print(f"Agent {self.model} failed: {e}")
            return f"Error: {str(e)}"

    async def generate_stream(self, user_prompt: str, context: Optional[str] = None):
        """Yields tokens as they are generated using NeuroVaultLLM."""
        messages = []
        if self.system_prompt:
            messages.append({'role': 'system', 'content': self.system_prompt})
        
        full_prompt = user_prompt
        if context:
            full_prompt += f"\n\nContext:\n{context}"
            
        messages.append({'role': 'user', 'content': full_prompt})

        try:
            async for chunk in await NeuroVaultLLM.chat(model=self.model, messages=messages, stream=True):
                content = chunk['message']['content']
                if content:
                    yield content
        except Exception as e:
            print(f"Agent {self.model} stream failed: {e}")
            yield f" [Error: {str(e)}] "
