from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import os

from db.database import get_db
from app.models.base import Note
from app.schemas.note import NoteCreate, NoteResponse, SearchResult
from app.services.note_service import NoteService

router = APIRouter()

@router.get("/tasks", response_model=list[NoteResponse])
async def get_tasks(
    db: AsyncSession = Depends(get_db),
    include_completed: bool = False
):
    query = select(Note).where(Note.is_task == True, Note.is_active == True)
    
    if not include_completed:
        query = query.where(Note.is_completed == False)
        
    query = query.order_by(Note.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()

@router.patch("/notes/{note_id}/complete", response_model=NoteResponse)
async def complete_task(
    note_id: int,
    completed: bool = True,
    db: AsyncSession = Depends(get_db)
):
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
        
    note.is_completed = completed
    await db.commit()
    await db.refresh(note)
    return note

@router.get("/notes/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: int,
    db: AsyncSession = Depends(get_db)
):
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks

@router.post("/notes", response_model=NoteResponse)
async def create_note(
    note_in: NoteCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new note.
    Triggers vectorization automatically.
    Background: Summarization.
    """
    try:
        note = await NoteService.create_note(db, note_in)
        
        # Fire & Forget Summary
        if len(note_in.content) > 500 and not getattr(note_in, 'is_hidden', False):
             background_tasks.add_task(NoteService.background_summarize_note, note.id)
             
        return note
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/timeline", response_model=List[NoteResponse])
async def get_timeline(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent notes (timeline).
    """
    return await NoteService.get_timeline(db, skip, limit)

@router.get("/search", response_model=List[SearchResult])
async def search_notes(
    q: str,
    limit: int = 10,
    media_type: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Semantic search for notes.
    """
    """
    """
    if not q and not media_type:
        return []
    return await NoteService.search_notes(db, q, limit, media_type)

@router.delete("/notes/{note_id}")
async def delete_note(
    note_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a note permanently.
    """
    success = await NoteService.delete_note(db, note_id)
    if not success:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"status": "success"}

@router.post("/notes/{note_id}/retry", response_model=NoteResponse)
async def retry_note_processing(
    note_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Retry analysis for a failed note (Image/Voice).
    """
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
        
    # Determine type
    is_image = "image" in note.tags or note.media_type == "image"
    is_voice = "voice" in note.tags or note.media_type == "voice"
    is_pdf = "pdf" in note.tags or note.media_type == "pdf"
    
    if not note.file_path or not os.path.exists(note.file_path):
        raise HTTPException(status_code=400, detail="Original file missing.")

    # Reset State
    await NoteService.update_note(db, note_id, {
        "is_processing": True,
        # Remove 'processing_failed' tag if exists
        "tags": [t for t in note.tags if t != "processing_failed"]
    })
    
    # Dispatch Task
    from app.api.upload import process_image_task, process_audio_task, process_pdf_task
    
    if is_image:
        background_tasks.add_task(process_image_task, note.file_path, note.id)
    elif is_voice:
        background_tasks.add_task(process_audio_task, note.file_path, note.id)
    elif is_pdf:
        background_tasks.add_task(process_pdf_task, note.file_path, note.id)
    else:
        # Just a text note? Re-run LLM?
        # Assuming only files need retry for now.
        pass
        
    return note
