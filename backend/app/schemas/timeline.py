from datetime import date, datetime
from typing import List
from pydantic import BaseModel, ConfigDict, model_validator
from app.schemas.note import NoteResponse

class TaskItem(BaseModel):
    task: str
    priority: str
    timeline: str

class SummaryResponse(BaseModel):
    id: int
    date_bucket: datetime | date
    summary_text: str
    linked_note_ids: List[int]
    created_at: datetime
    tasks: List[TaskItem] = []

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='after')
    def parse_tasks_from_summary(self):
        if not self.tasks and self.summary_text:
            text = self.summary_text.strip()
            # Handle markdown code blocks
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            try:
                import json
                parsed = json.loads(text.strip())
                
                tasks_data = []
                if isinstance(parsed, list):
                    tasks_data = parsed
                elif isinstance(parsed, dict) and "tasks" in parsed:
                    tasks_data = parsed["tasks"]
                
                # Check format
                validated_tasks = []
                for t in tasks_data:
                    if isinstance(t, dict) and "task" in t:
                        # Ensure all fields exist
                        validated_tasks.append(TaskItem(
                            task=t.get("task", ""),
                            priority=t.get("priority", "Medium"),
                            timeline=t.get("timeline", "Upcoming")
                        ))
                
                self.tasks = validated_tasks
            except Exception as e:
                # If parsing fails, just leave tasks empty. Don't crash.
                print(f"JSON Parse error in SummaryResponse: {e}")
                pass
        return self

class TimelineResponse(BaseModel):
    date: date
    summary: SummaryResponse | None
    notes: List[NoteResponse]
