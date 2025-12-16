# API Logic Documentation

This directory contains the FastAPI route definitions.

## Files & Functions

### `chat.py`
User-facing endpoint for the Agentic Chat.
- **`POST /api/chat/pdf/{note_id}`**:
    - **Input**: `note_id` (PDF Parent ID), `query` (User question).
    - **Logic**:
        1.  Calls `NoteService.get_note_context` to find relevant chunks.
        2.  Invokes `MessengerAgent` to draft an answer.
        3.  Invokes `AuditorAgent` to verify the answer.
    - **Output**: JSON with `answer`, `verified` (bool), and `correction` (if any).

### `notes.py`
Standard CRUD for Notes.
- **`POST /api/notes`**: Creates a new text note. Triggers auto-summary if >500 chars.
- **`GET /api/timeline`**: Returns recent notes, **excluding** hidden PDF chunks.
- **`GET /api/tasks`**: Returns active tasks (notes with `is_task=True`).
- **`PATCH /api/notes/{note_id}/complete`**: Marks a task as completed/incomplete.
- **`GET /api/search`**: Performs hybrid search using `NoteService.search_notes`.
- **`DELETE /api/notes/{note_id}`**: Hard delete. Cascades to file system and vector DB.

### `summary.py`
Rolling Updates logic.
- **`GET /api/summary`**: Returns the computed daily summary.
- **`POST /api/summary/refresh`**: Triggers `SummaryService.generate_summary` using `gemma3:4b` to analyze recent notes and extract tasks.

### `upload.py`
File Ingestion.
- **`POST /api/upload`**:
    - **Supported Types**: Image (`caption`), Audio (`transcribe`), PDF (`chunk`).
    - **PDF Logic**:
        -   Creates **1 Parent Note** (Visible, truncated content).
    -   *Key Logic*: For PDFs, it creates a **Parent Note** (visible) and multiple **Child Notes** (chunks, hidden).
        -   Only Parent is shown in Timeline; Children are used for RAG.

### `voice.py`
Endpoint for Voice Interaction.
- **`POST /api/voice/command`**:
    - **Inputs**: `text` (string) OR `file` (audio upload).
    - **Logic**:
        -   If file: Calls `VoiceService.transcribe` (Whisper) -> `VoiceService.process_command`.
        -   If text: Calls `VoiceService.process_command`.
        -   Agent determines intent (Query, Action, or Chat).
        -   Generates Audio response using `VoiceService.speak` (Kokoro).
    - **Output**: JSON with `response`, `audio` (base64 wav), `intent`.
- **`POST /api/voice/pdf/{note_id}`**:
    - Direct voice interaction with a specific PDF note.
- **`POST /api/voice/pdf/{note_id}/stream`**:
    - Streaming voice interaction (SSE) with a PDF note.
