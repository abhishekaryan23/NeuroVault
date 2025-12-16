from datetime import datetime
from enum import Enum
from typing import List, Optional
from sqlalchemy import Integer, String, Boolean, DateTime, Date, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON

class MediaType(str, Enum):
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    LINK = "link"
    PDF = "pdf"

class Base(DeclarativeBase):
    pass

class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # UI Summary for large notes
    file_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    media_type: Mapped[MediaType] = mapped_column(String, default=MediaType.TEXT)
    tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Hierarchical Notes (PDF Parent -> Chunk Children)
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # ForeignKey could be added but recursive FKs in same table tricky in simple setups
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False) # For chunks that shouldn't clutter timeline
    is_processing: Mapped[bool] = mapped_column(Boolean, default=False) # For async ingestion

    # Task / Todo Fields
    is_task: Mapped[bool] = mapped_column(Boolean, default=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Source Tracking & Event Scheduling
    origin_note_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # ID of the voice/text note this task was extracted from
    event_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True) # Specific scheduled time for events
    event_duration: Mapped[int] = mapped_column(Integer, default=60) # Duration in minutes


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_bucket: Mapped[datetime] = mapped_column(Date)
    summary_text: Mapped[str] = mapped_column(Text)
    linked_note_ids: Mapped[List[int]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
