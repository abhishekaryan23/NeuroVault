from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from db.database import get_db
from app.services.voice_service import VoiceService
from starlette.responses import StreamingResponse
import json

router = APIRouter()

class VoiceCommandResponse(BaseModel):
    response: str
    audio: str | None = None
    action_taken: str | None = None
    intent: str | None = None
    query: str | None = None

@router.post("/voice/command", response_model=VoiceCommandResponse)
async def process_voice_command(
    text: str = Form(None), # Optional text input
    file: UploadFile = File(None), # Optional audio file
    stt_only: bool = Form(False),
    speak: bool = Form(True), # Controls audio generation
    db: AsyncSession = Depends(get_db)
):
    """
    Process a voice command.
    Accepts EITHER 'text' (JSON/Form) OR 'file' (Audio WAV).
    If stt_only=True, returns purely the transcribed text.
    """
    result = {"response": "No input provided."}
    
    if file:
        audio_bytes = await file.read()
        if stt_only:
             # Direct STT bypassing the agent logic
             transcribed_text = await VoiceService.transcribe(audio_bytes)
             return VoiceCommandResponse(
                 response=transcribed_text,
                 intent="STT_ONLY"
             )
             
        result = await VoiceService.process_audio(db, audio_bytes)
    elif text:
        result = await VoiceService.process_command(db, text, generate_audio=speak)
        
    return VoiceCommandResponse(
        response=result.get("response"),
        audio=result.get("audio"),
        action_taken=result.get("action_taken"),
        intent=result.get("intent"),
        query=result.get("query")
    )

@router.post("/voice/pdf/{note_id}", response_model=VoiceCommandResponse)
async def chat_with_pdf_voice(
    note_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Direct voice interaction with a specific PDF note.
    File must be audio (WAV/WebM).
    Returns transcribed text as 'query', answer as 'response', and 'audio'.
    """
    audio_bytes = await file.read()
    result = await VoiceService.process_pdf_audio(db, audio_bytes, note_id)
    
    return VoiceCommandResponse(
        response=result.get("response"),
        audio=result.get("audio"),
        query=result.get("user_text"),
        intent="PDF_CHAT"
    )

@router.post("/voice/pdf/{note_id}/stream")
async def stream_pdf_audio(
    note_id: int,
    file: UploadFile = File(...),
    # db: AsyncSession = Depends(get_db) # Remove Depends to manage lifecycle manually
):
    """
    Streaming Endpoint for Voice Chat with PDF.
    Manages DB session manually to ensure it closes BEFORE long streaming starts.
    """
    audio_bytes = await file.read()
    
    # 1. Transcribe (No DB)
    from app.services.voice_service import VoiceService
    text = await VoiceService.transcribe(audio_bytes)
    
    if not text:
        # Return simple stream saying "I didn't hear you"
        async def empty_gen():
            yield f"data: {json.dumps({'response': 'I did not hear anything.'})}\n\n"
        return StreamingResponse(empty_gen(), media_type="text/event-stream")

    # 2. Get Context (Short-lived DB Session)
    from db.database import async_session_maker
    from app.services.note_service import NoteService
    
    context_chunks = []
    
    # Use context manager to ensure session closes immediately
    async with async_session_maker() as db:
        try:
            # We could verify note_id exists here too
            context_chunks = await NoteService.get_note_context(db, note_id, text)
        except Exception as e:
            print(f"[Streaming] DB Error: {e}")
            pass
            
    # 3. Stream Response (Pure CPU/Network, No DB)
    # The session 'db' is successfully closed here.
    return StreamingResponse(
        VoiceService.generate_pdf_response_stream(text, context_chunks, note_id),
        media_type="text/event-stream"
    )
