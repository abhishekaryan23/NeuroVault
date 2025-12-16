from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from db.database import get_db
from app.services.note_service import NoteService
from app.agents.messenger import MessengerAgent
from app.agents.auditor import AuditorAgent

router = APIRouter()

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    answer: str
    verified: bool
    correction: str | None = None

# Initialize Agents
# In a real app, maybe dependency inject them, but global is fine here
messenger = MessengerAgent()
auditor = AuditorAgent()

from fastapi.responses import StreamingResponse
import json
import time

@router.post("/chat/pdf/{note_id}/stream")
async def chat_with_pdf_stream(
    note_id: int,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Streaming Dual-Agent Chat.
    """
    start_time = time.time()
    print(f"[Chat] Starting request for note {note_id}")
    
    # 1. Get Context
    context_chunks = await NoteService.get_note_context(db, parent_id=note_id, query_text=request.query)
    print(f"[Chat] Context retrieved in {time.time() - start_time:.2f}s. Chunks: {len(context_chunks)}")
    
    if not context_chunks:
        async def empty_stream():
            yield "data: I couldn't find any relevant information in this document.\n\n"
            data = json.dumps({"verified": True})
            yield f"event: verification\ndata: {data}\n\n"
        return StreamingResponse(empty_stream(), media_type="text/event-stream")

    async def event_generator():
        # 2. Messenger (Stream)
        print(f"[Chat] Starting Messenger stream...")
        stream_start = time.time()
        full_answer = ""
        first_token_seen = False
        
        async for token in messenger.stream_answer_with_rag(request.query, context_chunks):
            if not first_token_seen:
                print(f"[Chat] TTFT (First Token): {time.time() - stream_start:.2f}s")
                first_token_seen = True
                
            full_answer += token
            # SSE Format
            data = json.dumps({"token": token})
            yield f"data: {data}\n\n"
        
        print(f"[Chat] Messenger done in {time.time() - stream_start:.2f}s. Starting Auditor...")
        
        # 3. Auditor (Verify) - Background
        verification = await auditor.verify(request.query, full_answer, context_chunks)
        print(f"[Chat] Auditor done.")
        
        # Send Verification Event
        v_data = json.dumps({"verified": verification.get("is_valid"), "correction": verification.get("correction"), "reason": verification.get("reason"), "type": "verification"})
        yield f"data: {v_data}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
