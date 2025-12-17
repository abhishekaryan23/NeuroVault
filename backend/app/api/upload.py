
import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Form
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.config import settings
from app.services.multimodal_service import MultimodalService
from app.services.note_service import NoteService
from app.schemas.note import NoteCreate, NoteResponse
from app.models.base import MediaType
from db.database import get_db

router = APIRouter()

# Global Semaphore to limit concurrent LLM tasks
import asyncio
llm_semaphore = asyncio.Semaphore(1) # Limit to 1 concurrent task

async def run_with_semaphore(coro):
    async with llm_semaphore:
        return await coro

class UploadResponse(BaseModel):
    file_path: str
    media_type: str
    extracted_content: str
    tags: List[str] = []
    chunks_created: int = 0

def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
    return chunks

# Background processing placeholder removed for clarity


from db.database import async_session_maker

def extract_pdf_text_sync(file_path: str) -> str:
    """Synchronous PDF extraction to be run in executor."""
    import pypdf
    reader = pypdf.PdfReader(file_path)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"
    return full_text

async def process_pdf_task(file_path: str, parent_note_id: int):
    """Background task to chunk and embed PDF."""
    from app.services.summary_service import SummaryService
    from sqlalchemy import select
    from app.models.base import Note
    
    async with async_session_maker() as db:
        try:
            print(f"[PDF] Starting background processing for {file_path}")
            
            # Run CPU-bound extraction in thread pool
            import asyncio
            loop = asyncio.get_running_loop()
            full_text = await loop.run_in_executor(None, extract_pdf_text_sync, file_path)
            
            if not full_text:
                print(f"[PDF] Warning: No text extracted from {file_path}")
                full_text = "(Empty PDF)"

            # 1. Summarize the PDF (Update Parent)
            summary_text = await SummaryService.summarize_single_note(full_text[:10000])
            
            # Update Parent Note with Summary
            stmt = select(Note).where(Note.id == parent_note_id)
            result = await db.execute(stmt)
            parent_note = result.scalars().first()
            if parent_note:
                parent_note.summary = summary_text
                # Optional: Append summary to content so it's searchable? 
                # Or keep content as "PDF: filename" and use summary field.
                # Let's keep content clean, but ensure summary is saved.
                await db.commit()
                print(f"[PDF] Summary generated: {summary_text[:50]}...")

                # NEW: Index the Parent Note itself using its Summary!
                # This ensures the File itself appears in search results, not just its chunks.
                from app.services.vector_service import VectorService
                from sqlalchemy import text
                import json
                
                # Construct enriched parent text
                # We use the filename (in content) + Summary + Tags
                parent_text = f"Type: pdf\nTags: pdf, document\nSummary: {summary_text}\nContent: {parent_note.content}"
                
                try:
                    vector = await VectorService.embed_text(parent_text)
                    vec_stmt = text("INSERT INTO vec_notes(rowid, embedding) VALUES (:id, :embedding)")
                    await db.execute(vec_stmt, {"id": parent_note.id, "embedding": json.dumps(vector)})
                    await db.commit()
                    print(f"[PDF] Parent note {parent_note.id} indexed successfully.")
                except Exception as ve:
                    print(f"[PDF] Failed to index parent note: {ve}")
            
            # 2. Chunking
            chunks = chunk_text(full_text)
            print(f"[PDF] Created {len(chunks)} chunks.")
            
            for i, chunk in enumerate(chunks):
                child_in = NoteCreate(
                    content=chunk,
                    media_type=MediaType.PDF,
                    tags=["pdf", "chunk", f"part_{i+1}"],
                    file_path=file_path,
                    parent_id=parent_note_id,
                    is_hidden=True
                )
                # Create and Embed Chunk
                await NoteService.create_note(db, child_in)
                
            # Mark Parent as Ready
            await NoteService.mark_as_processed(db, parent_note_id)
            print(f"Background processing complete for note {parent_note_id}")
            
        except Exception as e:
            print(f"Background PDF processing failed: {e}")
            # Optionally mark as failed or handle error in DB

@router.post("/upload", response_model=Note) # Changed from UploadResponse to Note
async def upload_file(
    file: UploadFile = File(...),
    content: Optional[str] = Form(None), # Added content parameter
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db)
):
    """
    Unified Non-Blocking Upload:
    1. Saves File immediately.
    2. Creates Note immediately (is_processing=True).
    3. Offloads Analysis to Background Task.
    4. Returns Note immediately.
    """
    # 0. Size Limit Check (200MB)
    MAX_SIZE = 200 * 1024 * 1024 # 200MB
    # Check size by seeking to end
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0) # Reset position
    
    if file_size > MAX_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 200MB.")
    
    # 1. Determine Type
    content_type = file.content_type
    media_type = "file"
    is_image = content_type.startswith("image/")
    is_audio = content_type.startswith("audio/")
    is_pdf = content_type == "application/pdf"
    
    sub_dir = "others"
    if is_image:
        media_type = "image"
        sub_dir = "images"
    elif is_audio:
        media_type = "voice"
        sub_dir = "audio"
    elif is_pdf:
        media_type = "pdf"
        sub_dir = "pdf"
    
    # 2. Save File
    upload_path = os.path.join(settings.UPLOAD_DIR, sub_dir)
    os.makedirs(upload_path, exist_ok=True)
    
    file_location = os.path.join(upload_path, file.filename)
    
    try:
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")

    # 3. Create Note Immediately
    note_content = content if content else f"Processing {media_type}..."
    if is_pdf: note_content = f"PDF: {file.filename}"
    
    note_in = NoteCreate(
        content=note_content,
        media_type=MediaType(media_type), # Ensure MediaType enum is used
        tags=[media_type, "processing"],
        file_path=file_location,
        is_hidden=False,
        is_processing=True
    )
    note = await NoteService.create_note(db, note_in)

    # 4. Dispatch Background Task
    if is_pdf:
        background_tasks.add_task(process_pdf_task, file_location, note.id)
    elif is_image:
        background_tasks.add_task(process_image_task, file_location, note.id) # To be implemented
    elif is_audio:
        # TODO: Implement Audio Background Task or keep sync if fast? 
        # For uniformity, let's make it async too.
        background_tasks.add_task(process_audio_task, file_location, note.id) # To be implemented
    else:
        # Just a file upload, mark processed
        await NoteService.update_note(db, note.id, {"is_processing": False, "tags": [media_type]})

    return note


async def process_image_task(file_path: str, note_id: int):
    """Background Image Analysis"""
    async with async_session_maker() as db:
        try:
            print(f"[Image] Queued {file_path} for Note {note_id}")
            # Wait for Semaphore
            result = await run_with_semaphore(MultimodalService.process_image(file_path))
            
            description = ""
            tags = []
            if isinstance(result, dict):
                description = result.get("description", "")
                tags = result.get("tags", [])
            else:
                description = str(result)
            
            # Enrich tags
            tags.append("image")
            
            # Update Note
            current_note = await NoteService.get_note(db, note_id)
            new_content = description
            
            if current_note:
                if "Processing" in current_note.content:
                     new_content = description
                else:
                     new_content = f"{current_note.content}\n\n[AI Analysis]: {description}"

            await NoteService.update_note(db, note_id, {
                "content": new_content,
                "is_processing": False,
                "tags": list(set(current_note.tags + tags)) if current_note else tags
            })
            print(f"[Image] Finished Note {note_id}")

        except Exception as e:
            print(f"[Image] Failed: {e}")
            await NoteService.update_note(db, note_id, {
                "is_processing": False,
                "tags": ["processing_failed", "image"]
            })

async def process_audio_task(file_path: str, note_id: int):
    """Background Audio Transcription"""
    async with async_session_maker() as db:
        try:
            print(f"[Audio] Queued {file_path} for Note {note_id}")
            text = await run_with_semaphore(MultimodalService.process_audio(file_path))
            
            await NoteService.update_note(db, note_id, {
                "content": text,
                "is_processing": False,
                "tags": ["voice", "audio"]
            })
            print(f"[Audio] Finished Note {note_id}")
        except Exception as e:
            print(f"[Audio] Failed: {e}")
            await NoteService.update_note(db, note_id, {
                "is_processing": False,
                "tags": ["processing_failed", "voice"]
            })
