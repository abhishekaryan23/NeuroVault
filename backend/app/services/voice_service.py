import json
from datetime import datetime
from app.core.llm import NeuroVaultLLM
import httpx
import base64
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.core.prompts import Prompts
from app.services.note_service import NoteService
from app.schemas.note import NoteCreate

VOICE_ENGINE_URL = "http://localhost:8001"

class VoiceService:
    @staticmethod
    async def transcribe(audio_bytes: bytes) -> str:
        """
        Transcribe audio using the external Voice Engine (Faster Whisper).
        """
        try:
            async with httpx.AsyncClient() as client:
                files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
                resp = await client.post(f"{VOICE_ENGINE_URL}/stt", files=files, timeout=30.0)
                if resp.status_code == 200:
                    return resp.json().get("text", "")
                else:
                    print(f"STT Error {resp.status_code}: {resp.text}")
                    return ""
        except Exception as e:
            print(f"STT Connection Error: {e}")
            return ""

    @staticmethod
    async def process_audio(db: AsyncSession, audio_bytes: bytes, background_tasks=None) -> dict:
        """
        Transcribe audio, SAVE IT, and process command.
        """
        try:
            # 1. Save Audio File
            import uuid
            import os
            
            audio_filename = f"voice_{uuid.uuid4()}.wav"
            # Ensure directory exists
            audio_dir = "dumps/audio"
            os.makedirs(audio_dir, exist_ok=True)
            
            file_path = os.path.join(audio_dir, audio_filename)
            
            with open(file_path, "wb") as f:
                f.write(audio_bytes)
                
            print(f"[Voice] Audio saved to: {file_path}")
            
            # 2. Transcribe
            text = await VoiceService.transcribe(audio_bytes)
                
            if not text:
                return {"response": "I didn't catch that."}
                
            # 3. Process Text with Reference to Audio File
            return await VoiceService.process_command(db, text, audio_path=file_path, background_tasks=background_tasks)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[Voice] Audio process error: {e}")
            return {"response": f"Error processing audio: {str(e)}"}

    @staticmethod
    async def check_conflict(db: AsyncSession, start_time: datetime, duration_minutes: int) -> str | None:
        """
        Check if the proposed time overlaps with any existing event.
        Returns the content/name of the conflicting event, or None.
        """
        from app.models.base import Note
        from sqlalchemy import select, and_
        from datetime import timedelta
        
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        # Query active notes that have an event_at time
        # We need to fetch them to calculate end times (since DB doesn't store end_time explicitly yet for query, 
        # but we can do a broad check or fetch all today's events)
        # Proper SQL overlap check is harder without stored end_time.
        # Let's fetch active events around the target time window for simplicity.
        # Or better, fetch all events with event_at is not null. 
        # For scale, we should filter by day, but let's do all for now or filter > now.
        
        stmt = select(Note).where(
            Note.is_active == True,
            Note.event_at.is_not(None)
        )
        result = await db.execute(stmt)
        existing_events = result.scalars().all()
        
        print(f"[DEBUG] check_conflict: Found {len(existing_events)} existing events.")
        
        for event in existing_events:
            # Calculate existing event window
            # Uses default 60 if event_duration is missing (should be there after schema update)
            existing_start = event.event_at
            existing_duration = getattr(event, "event_duration", 60) 
            existing_end = existing_start + timedelta(minutes=existing_duration)
            
            print(f"[DEBUG] Checking against '{event.content}': {existing_start} - {existing_end} vs Target: {start_time} - {end_time}")
            
            # Check Overlap: (StartA < EndB) and (EndA > StartB)
            if (start_time < existing_end) and (end_time > existing_start):
                return event.content
                
        return None

    @staticmethod
    async def process_command(db: AsyncSession, text: str, audio_path: str = None, background_tasks=None, generate_audio: bool = True) -> dict:
        """
        Process a voice command.
        - Always creates a 'Source Note' first (Processing State).
        - If Text Mode (generate_audio=False): Returns immediately, processes in background.
        - If Voice Mode (generate_audio=True): Awaits processing, returns audio.
        """
        print(f"[Voice] Processing: {text}")
        
        # 1. Create Source Note Immediately (Processing State)
        source_note_in = NoteCreate(
            content=text,
            media_type="voice" if audio_path else "text",
            tags=["voice_dump"] if audio_path else ["text_dump", "processing"],
            is_hidden=False,
            file_path=audio_path,
            is_task=False,
            is_processing=True # Key for Skeleton Loading
        )
        source_note = await NoteService.create_note(db, source_note_in)
        print(f"[Voice] Created Source Note {source_note.id}, starting analysis...")

        # 2. Define Processing Logic (To be run sync or async)
        async def run_analysis(note_id: int):
            from db.database import async_session_maker
            # Create new session for background work
            async with async_session_maker() as session:
                return await VoiceService.analyze_and_update_note(session, note_id, text)

        # 3. Dispatch based on Mode
        if not generate_audio and background_tasks:
            # TEXT MODE: Fire & Forget
            # We return early so UI shows Skeleton
            background_tasks.add_task(run_analysis, source_note.id)
            return {
                "response": "Processing note...",
                "action_taken": "created_note",
                "audio": None,
                "note_id": source_note.id
            }
        else:
            # VOICE MODE: Await result (Interactive)
            # We reuse the logic but wait for it to get the audio/response
            # Note: We can reuse the SAME 'db' session here since we are awaiting before return
            result = await VoiceService.analyze_and_update_note(db, source_note.id, text)
            
            # Generate Audio
            audio_b64 = None
            if generate_audio and result.get("response"):
                 audio_b64 = await VoiceService.synthesize_audio(result.get("response"))
            
            result["audio"] = audio_b64
            return result

    @staticmethod
    async def analyze_and_update_note(db: AsyncSession, note_id: int, text: str) -> dict:
        """
        Core Logic: Two-Stage Pipeline (Router -> Parser)
        """
        response_text = ""
        category_intent = "SAVE" # Default
        result_list_for_ui = []
        
        # Imports needed for logic
        from pydantic import BaseModel
        from typing import Literal, Optional
        from datetime import datetime
        
        try:
            # --- PRE-PROCESSING ---
            # Heuristic: If > 100 words, it's definitely a Note (SAVE).
            word_count = len(text.split())
            if word_count > 100:
                print(f"[Voice] Word count {word_count} > 100. Skipping Router. Force SAVE.")
                category_intent = "SAVE"
            else:
                # --- STAGE 1: ROUTER ---
                print(f"[Voice] Stage 1: Router Analysis...")
                from pydantic import BaseModel
                from typing import Literal, Optional
                
                class RouterResponse(BaseModel):
                    category: Literal["ACTION", "SAVE"]
                    reasoning: Optional[str] = None
                    confidence: float
                
                router_res = await NeuroVaultLLM.chat(
                    model=settings.SUMMARY_MODEL,
                    messages=[{"role": "user", "content": Prompts.ROUTER_PROMPT.format(text=text)}],
                    format=RouterResponse.model_json_schema()
                )
                router_data = json.loads(router_res['message']['content'])
                category_intent = router_data.get("category", "SAVE")
                print(f"[Voice] Router Decision: {category_intent} (Conf: {router_data.get('confidence')})")

            # --- STAGE 2: PARSER ---
            from datetime import datetime
            now = datetime.now()
            current_time_str = now.strftime("%Y-%m-%d %H:%M:%S")

            if category_intent == "ACTION":
                # --- STAGE 2A: ACTION PARSER ---
                print(f"[Voice] Stage 2A: Action Parser...")
                
                class ActionResponse(BaseModel):
                    type: Literal["TASK", "EVENT", "SEARCH"]
                    summary: str
                    due_date: Optional[str] = None
                    time: Optional[str] = None
                    priority: int = 4
                    category: Literal["Work", "Personal", "Health", "Finance", "General"] = "General"
                    duration_minutes: int = 60

                action_res = await NeuroVaultLLM.chat(
                    model=settings.SUMMARY_MODEL,
                    messages=[{"role": "user", "content": Prompts.ACTION_PARSER_PROMPT.format(text=text, current_time=current_time_str)}],
                    format=ActionResponse.model_json_schema()
                )
                action_data = json.loads(action_res['message']['content'])
                action_type = action_data.get("type", "TASK")
                
                print(f"[Voice] Action Type: {action_type}")
                
                if action_type == "SEARCH":
                    # SEARCH LOGIC
                    await NoteService.delete_note(db, note_id) # Cleanup temp note
                    query = action_data.get("summary", text)
                    results = await NoteService.search_notes(db, query, limit=5)
                    
                    for r in results:
                        n = r['note']
                        result_list_for_ui.append({
                            "id": n.id, "content": n.content, "distance": r['distance'],
                            "created_at": n.created_at.isoformat()
                        })
                    
                    if not results:
                        response_text = f"No results for '{query}'."
                    else:
                        context_str = "\n".join([f"- {r['note'].content}" for r in results])
                        summary_prompt = Prompts.VOICE_SEARCH_SUMMARY_TEMPLATE.format(text=text, context_str=context_str)
                        s_res = await NeuroVaultLLM.generate(model=settings.SUMMARY_MODEL, prompt=summary_prompt)
                        response_text = s_res['response']
                        
                else: 
                    # TASK / EVENT LOGIC
                    content = action_data.get("summary", text)
                    cat = action_data.get("category", "General")
                    
                    # Construct Event Time
                    event_at_dt = None
                    due_date = action_data.get("due_date")
                    time_str = action_data.get("time")
                    
                    if due_date:
                        dt_str = f"{due_date} {time_str if time_str else '00:00:00'}"
                        try:
                            # Handle potential "Z" or format issues roughly
                            event_at_dt = datetime.fromisoformat(dt_str.replace("Z", ""))
                        except:
                            print(f"[Voice] Date Parse Failed: {dt_str}")
                    
                    # Conflict Check
                    duration = action_data.get("duration_minutes", 60)
                    conflict = None
                    if action_type == "EVENT" and event_at_dt:
                        conflict = await VoiceService.check_conflict(db, event_at_dt, duration)
                    
                    update_data = {
                        "content": content,
                        "is_processing": False,
                        "is_task": True,
                        "category": "Event" if action_type == "EVENT" else cat,
                        "event_at": event_at_dt,
                        "event_duration": duration,
                        "tags": ["task", cat.lower()] + (["event"] if action_type == "EVENT" else [])
                    }
                    
                    await NoteService.update_note(db, note_id, update_data)
                    
                    if action_type == "EVENT":
                         time_s = event_at_dt.strftime("%I:%M %p, %b %d") if event_at_dt else "scheduled time"
                         response_text = f"Scheduled '{content}' for {time_s}."
                         if conflict: response_text += f" Warning: Clash with '{conflict}'."
                    else:
                         response_text = f"Added '{content}' to {cat} list."

            else:
                # --- STAGE 2B: NOTE PROCESSOR (SAVE) ---
                print(f"[Voice] Stage 2B: Note Processor...")
                
                class NoteResponse(BaseModel):
                    generated_title: str
                    tags: list[str]
                    mentioned_entities: list[str]
                    is_voice_transcript: bool

                note_res = await NeuroVaultLLM.chat(
                    model=settings.SUMMARY_MODEL,
                    messages=[{"role": "user", "content": Prompts.NOTE_PROCESSOR_PROMPT.format(text=text)}],
                    format=NoteResponse.model_json_schema()
                )
                note_data = json.loads(note_res['message']['content'])
                
                tags = note_data.get("tags", [])
                if "note" not in tags: tags.append("note")
                
                # We append entities to tags for searchability? Or just store in summary?
                # For now, let's add entities as tags
                entities = note_data.get("mentioned_entities", [])
                safe_entities = [e.replace(" ", "_").lower() for e in entities]
                tags.extend(safe_entities)
                
                # Dedup tags
                tags = list(set(tags))
                
                update_data = {
                    "is_processing": False,
                    "tags": tags,
                    # We could update content to be cleaner, but user usually wants original dump.
                    # We might update summary field if we extracted a title?
                    # NoteService doesn't expose summary update easily unless we map it.
                    # Let's just update tags and status.
                }
                await NoteService.update_note(db, note_id, update_data)
                response_text = "Note saved."

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[Voice] Pipeline Error: {e}")
            response_text = "Error processing command."
            await NoteService.update_note(db, note_id, {"is_processing": False})

        return {
            "response": response_text,
            "intent": category_intent,
            "query": None, # Could populate if search
            "search_results": result_list_for_ui
        }

    @staticmethod
    async def synthesize_audio(text: str) -> str:
        """
        Call Voice Engine for Kokoro TTS.
        """
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{VOICE_ENGINE_URL}/tts", json={"text": text}, timeout=30.0)
                if resp.status_code == 200:
                    return resp.json().get("audio")
                else:
                    print(f"TTS Error {resp.status_code}: {resp.text}")
                    return None
        except Exception as e:
            print(f"TTS Connection Error: {e}")
            return None

    @staticmethod
    async def process_pdf_audio(db: AsyncSession, audio_bytes: bytes, note_id: int) -> dict:
        """
        Specialized flow for chatting with a PDF via Voice.
        1. Transcribe
        2. RAG (Context Search)
        3. LLM Answer
        4. TTS
        """
        try:
            # 1. Transcribe
            text = await VoiceService.transcribe(audio_bytes)
            if not text:
                return {"response": "I didn't hear anything.", "audio": None}
            
            print(f"[VoicePDF] User asked: {text}")

            # 2. Get Context from PDF
            # We assume note_id is the parent PDF note.
            context_chunks = await NoteService.get_note_context(db, note_id, text, top_k=3)
            context_str = "\n".join(context_chunks)
            
            # 3. Generate Answer
            system_prompt = Prompts.VOICE_PDF_RAG_TEMPLATE.format(
                context=context_chunks if context_chunks else "No relevant context found in document.",
                text=text
            )
            
            print(f"[VoicePDF] Generating answer with context len {len(context_str)}...")
            llm_res = await NeuroVaultLLM.generate(model=settings.SUMMARY_MODEL, prompt=system_prompt)
            answer = llm_res['response']
            print(f"[VoicePDF] Answer: {answer}")
            
            # 4. Generate Audio
            audio_b64 = await VoiceService.synthesize_audio(answer)
            
            return {
                "response": answer,
                "audio": audio_b64,
                "user_text": text
            }
            
        except Exception as e:
            print(f"[VoicePDF] Error: {e}")
            return {"response": "Sorry, I had an error.", "audio": None}

    @staticmethod
    async def generate_pdf_response_stream(text: str, context_chunks: list[str], note_id: int):
        """
        Pure generator that yields SSE events.
        Does NOT rely on DB. Context must be provided.
        """
        try:
             # Yield User Query for UI
            yield f"data: {json.dumps({'query': text})}\n\n"
            
            system_prompt = Prompts.VOICE_STREAM_SYSTEM_TEMPLATE.format(
                context=" ".join(context_chunks),
                text=text
            )
            
            # 3. Stream LLM (Text Only)
            sentence_buffer = ""
            full_answer = ""
            
            print(f"[VoiceStream] Streaming answer for: {text}")
            
            # Use NeuroVaultLLM for streaming
            import re

            # Async stream iteration - TEXT ONLY
            async for chunk in await NeuroVaultLLM.chat(model=settings.SUMMARY_MODEL, messages=[{'role': 'user', 'content': system_prompt}], stream=True):
                token = chunk['message']['content']
                yield f"data: {json.dumps({'token': token})}\n\n"
                full_answer += token
            
            # 4. Verification (Gemma 3)
            final_text_to_speak = full_answer
            try:
                from app.agents.auditor import AuditorAgent
                auditor = AuditorAgent()
                print(f"[VoiceStream] Verifying answer...")
                verification = await auditor.verify(text, full_answer, context_chunks)
                
                is_valid = verification.get("is_valid")
                correction = verification.get("correction")
                
                v_data = json.dumps({
                    "verified": is_valid,
                    "correction": correction,
                    "reason": verification.get("reason"),
                    "type": "verification"
                })
                yield f"data: {v_data}\n\n"

                # If verification failed and we have a correction, speak the CORRECTION instead?
                # Or just speak the original? Usually safer to speak the correction if it's a major error.
                # For now, let's speak the original unless the user wants strictness. 
                # Use the original full_answer to match what was typed on screen.
                # If we want to speak the correction, we should update final_text_to_speak.
                # final_text_to_speak = correction if correction else full_answer
                
            except Exception as e:
                print(f"[VoiceStream] Verification failed: {e}")

            # 5. Audio Generation (Post-Verification)
            # Now split the full text into sentences and stream audio
            print(f"[VoiceStream] Generating audio for verified text...")
            
            # Split into sentences using regex
            sentences = re.split(r'([.?!]+[\s]+)', final_text_to_speak)
            
            # The regex split keeps the delimiters. 
            # ["Hello", ". ", "How are you", "? ", ""]
            # We need to re-assemble or just iterate carefully.
            
            current_chunk = ""
            for part in sentences:
                current_chunk += part
                # If the part is a delimiter (ends with space/punctuation), it's a sentence end.
                if re.search(r'[.?!]+[\s]*$', part):
                    if len(current_chunk.strip()) > 0:
                        print(f"[VoiceStream] Synthesizing: {current_chunk[:20]}...")
                        audio_b64 = await VoiceService.synthesize_audio(current_chunk)
                        if audio_b64:
                            yield f"data: {json.dumps({'audio': audio_b64})}\n\n"
                        current_chunk = ""
            
            # Flush absolute last chunk
            if current_chunk.strip():
                 audio_b64 = await VoiceService.synthesize_audio(current_chunk)
                 if audio_b64:
                    yield f"data: {json.dumps({'audio': audio_b64})}\n\n"

            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            print(f"[VoiceStream] Error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
