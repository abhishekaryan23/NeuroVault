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

        class EventItem(BaseModel):
            title: str
            date_time: str
            duration_minutes: int = 60

        class RollingSummaryResponse(BaseModel):
            summary: str
            tasks: List[TaskItem]
            events: List[EventItem] = []

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
            
            # Extract and Save Tasks
            tasks_data = data.get("tasks", [])
            from app.schemas.note import NoteCreate
            from app.models.base import MediaType

            print(f"[Summary] Extracted {len(tasks_data)} tasks. Saving...")

            for t in tasks_data:
                try:
                    # Construct Note for the task
                    task_content = t.get("task")
                    if not task_content: continue
                    
                    priority = t.get("priority", "Medium")
                    timeline = t.get("timeline", "Today")
                    
                    task_note_in = NoteCreate(
                        content=task_content,
                        media_type=MediaType.TEXT,
                        tags=["todo", "ai-generated", priority, timeline],
                        is_task=True,
                        category=priority,
                        is_completed=False,
                        origin_note_id=notes[0].id if notes else None
                    )
                    
                    # Create the task note using NoteService
                    await NoteService.create_note(db, task_note_in)
                    
                except Exception as task_e:
                    print(f"Failed to create task note: {task_e}")

            # Extract and Save Events
            events_data = data.get("events", [])
            print(f"[Summary] Extracted {len(events_data)} events. Saving...")
            
            import dateparser
            
            for e in events_data:
                try:
                    event_title = e.get("title")
                    event_time_str = e.get("date_time")
                    if not event_title or not event_time_str: continue
                    
                    # Parse Date
                    event_dt = dateparser.parse(event_time_str, settings={'RELATIVE_BASE': datetime.datetime.now(), 'PREFER_DATES_FROM': 'future'})
                    
                    if not event_dt:
                        print(f"Could not parse date for event: {event_time_str}")
                        continue
                        
                    event_note_in = NoteCreate(
                        content=event_title,
                        media_type=MediaType.TEXT,
                        tags=["event", "ai-generated"],
                        is_task=True,
                        category="Event",
                        is_completed=False,
                        origin_note_id=notes[0].id if notes else None,
                        event_at=event_dt,
                        event_duration=e.get("duration_minutes", 60)
                    )
                     # Create the event note
                    await NoteService.create_note(db, event_note_in)
                    print(f"Created event: {event_title} at {event_dt}")
                    
                except Exception as event_e:
                    print(f"Failed to create event note: {event_e}")

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
