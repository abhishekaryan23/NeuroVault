from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field
from app.models.base import MediaType

class NoteBase(BaseModel):
    content: str
    media_type: MediaType = MediaType.TEXT
    tags: List[str] = Field(default_factory=list)

class NoteCreate(NoteBase):
    file_path: Optional[str] = None
    parent_id: Optional[int] = None
    is_hidden: bool = False
    is_processing: bool = False
    is_task: bool = False
    is_completed: bool = False
    category: Optional[str] = None
    origin_note_id: Optional[int] = None
    event_at: Optional[datetime] = None
    event_duration: int = 60

class NoteResponse(NoteBase):
    id: int
    content: str
    summary: Optional[str] = None
    file_path: Optional[str] = None
    parent_id: Optional[int] = None
    is_hidden: bool = False
    is_processing: bool = False
    is_task: bool = False
    is_completed: bool = False
    category: Optional[str] = None
    origin_note_id: Optional[int] = None
    event_at: Optional[datetime] = None
    event_duration: int = 60
    created_at: datetime
    updated_at: datetime
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)

class SearchResult(BaseModel):
    note: NoteResponse
    distance: float
