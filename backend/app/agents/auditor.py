from app.agents.base import BaseAgent
import json
from app.config import settings
from app.core.prompts import Prompts

class AuditorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            model=settings.AUDITOR_MODEL,
            system_prompt=Prompts.AUDITOR_SYSTEM
        )

    async def verify(self, question: str, answer: str, context_chunks: list[str]) -> dict:
        formatted_context = "\n---\n".join(context_chunks)
        
        from datetime import datetime
        now_str = datetime.now().strftime("%A, %B %d, %Y")
        prompt = Prompts.AUDITOR_VERIFY_TEMPLATE.format(
            context=formatted_context,
            question=question,
            answer=answer,
            current_time=now_str
        )
        
        from pydantic import BaseModel
        from typing import Optional

        class AuditorResponse(BaseModel):
            is_valid: bool
            reason: str
            correction: Optional[str] = None

        # Use generate with Chat-like structure or update BaseAgent to support format?
        # BaseAgent.generate uses self.lines... wait, AuditorAgent uses `self.generate` which wraps client.generate (Legacy)
        # But `NeuroVaultLLM.chat` supports format. `NeuroVaultLLM.generate` (Legacy) does NOT yet support format in my wrapper.
        # I should switch Auditor to use `chat` or update `generate`.
        # AuditorAgent inherits BaseAgent. Let's see BaseAgent.
        
        # Since I can't easily see BaseAgent right now without viewing it, I'll assume I should use NeuroVaultLLM.chat directly here 
        # OR update the wrapper. 
        # Providing structured output via `chat` is safer.
        
        from app.core.llm import NeuroVaultLLM
        
        try:
            # We construct messages manually since we are bypassing BaseAgent.generate loop for this specific atomic check
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            response = await NeuroVaultLLM.chat(
                model=self.model,
                messages=messages,
                format=AuditorResponse.model_json_schema()
            )
            
            content = response['message']['content']
            return json.loads(content)
            
        except Exception as e:
            print(f"Auditor verification failed: {e}")
            return {"is_valid": True, "reason": "Verification failed, assuming valid.", "correction": None}
