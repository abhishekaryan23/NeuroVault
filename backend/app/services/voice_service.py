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
    async def process_audio(db: AsyncSession, audio_bytes: bytes) -> dict:
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
            return await VoiceService.process_command(db, text, audio_path=file_path)
            
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
    async def process_command(db: AsyncSession, text: str, audio_path: str = None, generate_audio: bool = True) -> dict:
        """
        Process a voice command via LLM and execute actions.
        Returns dict with text response and audio.
        """
        print(f"[Voice] Processing: {text}")
        response_text = ""
        intent = "CHAT"
        query = None
        
        # 1. Intent Classification
        from datetime import datetime
        now = datetime.now()
        current_time_str = now.strftime("%A, %B %d, %Y at %I:%M %p")
        # Explicitly state "Today is..." to help LLM anchor
        context_str = f"Today is {now.strftime('%A, %B %d, %Y')}. Current time is {now.strftime('%I:%M %p')}."
        
        print(f"[Voice] Context: {context_str}")
        prompt = Prompts.VOICE_INTENT_TEMPLATE.format(text=text, current_time_context=context_str)
        
        from pydantic import BaseModel
        from typing import Optional, Literal

        class VoiceIntentResponse(BaseModel):
            intent: Literal["CREATE_NOTE", "TASK", "EVENT", "SEARCH", "CHAT"]
            content: Optional[str] = None
            category: Optional[Literal["Work", "Personal", "Home", "Health", "Finance", "Shopping", "Urgent", "Event"]] = None
            today_context: Optional[str] = None # Echo today's date from context for grounding
            time_expression: Optional[str] = None # Extraction of "tomorrow at 5pm", "next friday"
            event_datetime: Optional[str] = None # Fallback ISO calculation
            event_duration: Optional[int] = 60
            query: Optional[str] = None
            search_date_start: Optional[str] = None
            search_date_end: Optional[str] = None
            response: Optional[str] = None

        try:
            # fast classification
            print(f"[Voice] Sending to LLM ({settings.SUMMARY_MODEL})...")
            
            # Use Structured Outputs
            llm_response = await NeuroVaultLLM.chat(
                model=settings.SUMMARY_MODEL, 
                messages=[
                    {"role": "user", "content": prompt}
                ], 
                format=VoiceIntentResponse.model_json_schema()
            )
            
            result_json = llm_response['message']['content']
            data = json.loads(result_json)
            intent = data.get("intent", "CHAT")
            
            print(f"[Voice] Intent: {intent}")
            
            if intent in ["CREATE_NOTE", "TASK", "EVENT"]:
                # Phase 1: Always create the Source Note (Voice/Text Dump)
                source_note_in = NoteCreate(
                    content=text, # The full transcript
                    media_type="voice" if audio_path else "text",
                    tags=["voice_dump"] if audio_path else ["text_dump"],
                    is_hidden=False, 
                    file_path=audio_path,
                    is_task=False
                )
                source_note = await NoteService.create_note(db, source_note_in) 
                
                # Phase 2: Create the Task/Event Node if applicable
                is_task_intent = (intent in ["TASK", "EVENT"])
                
                if is_task_intent:
                    content = data.get("content", text)
                    if intent == "EVENT":
                        category = "Event"
                    else:
                        category = data.get("category")
                    
                    # Parse Event Time via Python (Robust)
                    event_at_dt = None
                    time_expression = data.get("time_expression")
                    llm_iso_date = data.get("event_datetime")
                    
                    print(f"[Voice] Time Extraction: Expr='{time_expression}', ISO='{llm_iso_date}'")

                    if time_expression:
                        import dateparser
                        # Use current time as anchor
                        event_at_dt = dateparser.parse(
                            time_expression, 
                            settings={'RELATIVE_BASE': now, 'PREFER_DATES_FROM': 'future'}
                        )
                    
                    # Fallback to LLM ISO if python parsing failed or missing expr
                    if not event_at_dt and llm_iso_date:
                        try:
                            clean_date = llm_iso_date.replace("Z", "").strip()
                            if "T" not in clean_date and " " in clean_date:
                                clean_date = clean_date.replace(" ", "T")
                            if "." in clean_date:
                                clean_date = clean_date.split(".")[0]
                            event_at_dt = datetime.fromisoformat(clean_date)
                        except Exception as e:
                            print(f"[Voice] Fallback Date Parse Error: {e}")
                            
                    print(f"[Voice] Final Calculated Date: {event_at_dt}")

                    # CONFLICT DETECTION
                    duration = data.get("event_duration", 60)
                    conflict_name = None
                    if event_at_dt:
                        conflict_name = await VoiceService.check_conflict(db, event_at_dt, duration)
                        if conflict_name:
                             print(f"[Voice] Conflict Detected with '{conflict_name}'")

                    task_note_in = NoteCreate(
                        content=content,
                        media_type="text", # The task itself is text
                        tags=["task", category.lower()] if category else ["task"],
                        # HIDE the generated task note from timeline (Agenda will fetch it via specific API)
                        # The Source Note is already visible in timeline, so we avoid duplicates.
                        is_hidden=True, 
                        is_task=True,
                        category=category,
                        origin_note_id=source_note.id, # LINKING IS HERE
                        event_at=event_at_dt,
                        event_duration=duration
                    )
                    await NoteService.create_note(db, task_note_in)
                
                if intent == "EVENT":
                        time_str = event_at_dt.strftime("%I:%M %p, %a %b %d") if event_at_dt else (time_expression or "scheduled time")
                        response_text = f"I've scheduled '{content}' for {time_str}."
                        if conflict_name:
                            response_text += f" Warning: You have a clash with '{conflict_name}'."
                elif is_task_intent:
                    response_text = f"I've added '{content}' to your {category or 'General'} list."
                else:
                    response_text = f"I've saved that note."
                
            elif intent == "SEARCH":
                query = data.get("query", text)
                
                # Parse search dates
                start_date_str = data.get("search_date_start")
                end_date_str = data.get("search_date_end")
                start_date = None
                end_date = None
                
                if start_date_str and end_date_str:
                     try:
                        clean_start = start_date_str.replace("Z", "").replace(" ", "T")
                        clean_end = end_date_str.replace("Z", "").replace(" ", "T")
                        if "." in clean_start: clean_start = clean_start.split(".")[0]
                        if "." in clean_end: clean_end = clean_end.split(".")[0]
                        start_date = datetime.fromisoformat(clean_start)
                        end_date = datetime.fromisoformat(clean_end)
                        print(f"[Voice] Search Date Range: {start_date} - {end_date}")
                     except Exception as e:
                        print(f"[Voice] Search Date Parse Error: {e}")

                results = await NoteService.search_notes(db, query, limit=5, start_date=start_date, end_date=end_date)
                
                # Add raw results for Frontend Modal
                result_list_for_ui = []
                for r in results:
                    note_obj = r['note']
                    # Convert to simple dict
                    result_list_for_ui.append({
                        "id": note_obj.id,
                        "content": note_obj.content,
                        "event_at": note_obj.event_at.isoformat() if note_obj.event_at else None,
                        "created_at": note_obj.created_at.isoformat(),
                        "distance": r['distance']
                    })

                if not results:
                    response_text = f"I couldn't find anything matching '{query}' in that time range."
                else:
                    context_str = "\n".join([f"- {r['note'].content} (Date: {r['note'].created_at})" for r in results])
                    summary_prompt = Prompts.VOICE_SEARCH_SUMMARY_TEMPLATE.format(
                        text=text,
                        context_str=context_str
                    )
                    summary_res = await NeuroVaultLLM.generate(model=settings.SUMMARY_MODEL, prompt=summary_prompt)
                    response_text = summary_res['response']
                    
                # Append to result dict later

                
            else: # CHAT
                response_text = data.get("response", "I'm listening.")
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[Voice] Error: {e}")
            response_text = f"I'm sorry, I had trouble processing that command. Error: {str(e)}"
            
        # Generate Audio via Voice Engine (Kokoro)
        audio_b64 = None
        if generate_audio:
            audio_b64 = await VoiceService.synthesize_audio(response_text)
        
        result = {
            "response": response_text, 
            "audio": audio_b64,
            "audio": audio_b64,
            "intent": intent,
            "query": query,
            "search_results": locals().get("result_list_for_ui", []) 
        }
             
        return result

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
