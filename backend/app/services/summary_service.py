from app.core.llm import NeuroVaultLLM
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.base import Summary
from app.api.notes import NoteService
from app.config import settings
from app.core.prompts import Prompts
import datetime

class SummaryService:
    @staticmethod
    async def generate_summary(db: AsyncSession) -> Summary:
        # 1. Fetch recent notes (e.g. last 20 or last 24 hours)
        # For simplicity, let's take last 10 notes to summarize context
        notes = await NoteService.get_timeline(db, limit=10)
        
        if not notes:
            return None
            
        # Format notes for prompt
        notes_text = "\n".join([f"- [{n.created_at}] {n.content}" for n in notes])
        
        now_str = datetime.datetime.now().strftime("%A, %B %d, %Y")
        prompt = Prompts.SUMMARY_GENERATION_TEMPLATE.format(notes_text=notes_text, current_time=now_str)
        
        # Define Schema
        from pydantic import BaseModel
        from typing import List, Literal

        class TaskItem(BaseModel):
            task: str
            priority: Literal["High", "Medium", "Low"]
            timeline: Literal["Today", "This Week", "Upcoming"]

        class RollingSummaryResponse(BaseModel):
            summary: str
            tasks: List[TaskItem]

        try:
            # Use Structured Outputs
            response = await NeuroVaultLLM.chat(
                model=settings.SUMMARY_MODEL, 
                messages=[
                    {'role': 'user', 'content': prompt},
                ],
                format=RollingSummaryResponse.model_json_schema()
            )
            
            summary_json_str = response['message']['content']
            import json
            data = json.loads(summary_json_str)
            summary_content = data.get("summary", "")
            # Note: The tasks extracted here are currently not used/saved in the next block
            # (The code below only saves summary_text). 
            # If we want to use tasks, we should save them too, but keeping scope minimal for now.
            # Just ensuring the summary generation is robust.
            
            # create summary record
            new_summary = Summary(
                summary_text=summary_content,
                date_bucket=notes[0].created_at, # Using most recent note date as bucket anchor
                linked_note_ids=[n.id for n in notes]
            )
            db.add(new_summary)
            await db.commit()
            await db.refresh(new_summary)
            return new_summary
            
        except Exception as e:
            print(f"Summary generation failed: {e}")
            return None

    @staticmethod
    async def get_latest_summary(db: AsyncSession) -> Summary:
        stmt = select(Summary).order_by(desc(Summary.created_at)).limit(1)
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def summarize_single_note(text: str) -> str:
        """
        Produce a concise summary for a large note.
        """
        # Truncate if insanely large to avoid context blowing
        if len(text) > 10000:
            text = text[:10000] + "...(truncated)"
            
        prompt = Prompts.SUMMARY_SINGLE_NOTE_TEMPLATE.format(text=text)
        try:
             response = await NeuroVaultLLM.chat(model=settings.SUMMARY_MODEL, messages=[
                {'role': 'user', 'content': prompt},
            ])
             return response['message']['content'].strip()
        except Exception as e:
            print(f"Single note summary failed: {e}")
            return text[:200] + "..."
