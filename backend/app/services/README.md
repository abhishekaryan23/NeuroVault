# Services Documentation

Business logic and external integrations.

## Files & Functions

### `note_service.py`
**Class `NoteService`**
- **`create_note(db, note_in)`**:
    - Handles DB insertion.
    - Calls `SummaryService.summarize_single_note` if text > 500 chars.
    - Calls `VectorService.embed_text` and inserts into `vec_notes`.
- **`delete_note(db, note_id)`**:
    - Deletes physical file.
    - Deletes vector from `vec_notes`.
    - **Cascade**: If Parent, deletes all Child Chunks and their vectors.
    - **Invalidation**: If note was in "Rolling Summary", deletes the summary.
- **`get_note_context(db, parent_id, query)`**:
    - **Scoped RAG**: Fetches child chunks for `parent_id`.
    - Performs in-memory cosine similarity (using numpy) on their vectors to find top-k matches for `query`.

### `summary_service.py`
**Class `SummaryService`**
- **`generate_summary(db)`**:
    - Fetches recent notes.
    - prompts `gemma3:4b` to generate a structured JSON (Summary + Task List).
    - Enforces **Strict Task Extraction** (only explicit "TODO"/"Remind me").
- **`summarize_single_note(text)`**:
    - Helper for summarizing long individual notes.

### `vector_service.py`
**Class `VectorService`**
- **`embed_text(text)`**:
    - Wraps `ollama.embeddings(model='embeddinggemma')`.
    - Returns list of floats.

### `multimodal_service.py`
**Class `MultimodalService`**
- **`process_image(path)`**: Uses `gemma3n:e4b` (vision) to caption images.
- **`process_audio(path)`**: (Placeholder) Implementation for Whisper/Similar.

### `voice_service.py`
**Class `VoiceService`**
- Intermediary for the `voice_engine` microservice.
- **`transcribe(audio_bytes)`**: Sends audio to `voice_engine` for STT.
- **`speak(text)`**: Sends text to `voice_engine` for TTS.
- **`process_command(db, text)`**: Logic for interpreting voice intent (Search, Action, or Chat).
