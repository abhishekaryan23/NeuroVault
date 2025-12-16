# Open-GDR Backend Guide

This guide outlines the structure, key functions, and testing procedures for the Open-GDR Backend (`backend/`).

## Configuration (`backend/app/config.py`)
The application is configured using `pydantic-settings`. Key settings include:
-   **`PROJECT_NAME`**: Name of the application (default: "NeuroVault").
-   **`DATABASE_URL`**: Async SQLite database URL (default: `sqlite+aiosqlite:///./neurovault.db`).
-   **`UPLOAD_DIR`**: Directory for storing uploaded files (default: `dumps`).
-   **AI Models**:
    -   `EMBEDDING_MODEL`: defaults to `embeddinggemma`.
    -   `SUMMARY_MODEL`: defaults to `gemma3:4b`.
    -   `IMAGE_MODEL`: defaults to `gemma3:4b`.

## Directory Structure (`backend/app/`)

### 1. **API (`app/api/`)**
The entry points for the application.
-   **`notes.py`**: CRUD operations for Notes.
    -   `POST /api/notes`: Create generic notes.
    -   `GET /api/search`: Hybrid search (Vector + Text).
    -   `GET /api/timeline`: Fetch recent notes.
    -   `GET /api/tasks`: Fetch active tasks (supports `include_completed`).
    -   `PATCH /api/notes/{id}/complete`: Toggle task completion status.
    -   `DELETE /api/notes/{id}`: Hard delete note + file + vector.
-   **`summary.py`**: Rolling Updates logic.
    -   `GET /api/summary`: Get current summary.
    -   `POST /api/summary/refresh`: Force regeneration using `gemma3:4b`.
-   **`upload.py`**: File ingestion.
    -   `POST /api/upload`: Handles Images, Audio, and **PDFs**.
    -   *Key Logic*: For PDFs, it creates a **Parent Note** (visible) and multiple **Child Notes** (chunks, hidden).
-   **`chat.py`**: Agentic interaction.
    -   `POST /api/chat/pdf/{note_id}`: Triggers the **Dual-Agent RAG Pipeline**.
-   **`voice.py`**: Voice Command Interface.
    -   `POST /api/voice/command`: Handles logic for Voice Search/Actions. Accepts text or audio file. Returns response + TTS audio.
    -   `POST /api/voice/pdf/{note_id}`: Direct voice interaction with a specific PDF note.
    -   `POST /api/voice/pdf/{note_id}/stream`: Streaming voice interaction with a specific PDF note.

### 2. **Services (`app/services/`)**
The business logic layer.
-   **`note_service.py`**: Core CRUD + Vector logic.
    -   `create_note()`: Handles DB insert + Vector embedding + Auto-summary (>500 chars).
    -   `delete_note()`: Cascade deletes files and vectors; invalidates Rolling Summary.
    -   `get_note_context(parent_id, query)`: **Scoped RAG**. Searches only within a specific PDF's chunks.
-   **`summary_service.py`**:
    -   `generate_summary()`: Uses LLM to create "Rolling Updates" and "Task Lists".
    -   `summarize_single_note()`: Fast summary for long individual notes.
-   **`vector_service.py`**:
    -   `embed_text()`: Uses Ollama (`embeddinggemma`) to generate vectors.
-   **`multimodal_service.py`**:
    -   Handlers for Image Captioning (`gemma3n`) and Audio Transcription.

### 3. **Agents (`app/agents/`)**
The Autonomous Logic layer.
-   **`base.py`**: Generic wrapper for Ollama.
-   **`messenger.py` (`gemma3:4b`)**: **The Generator**. Fast, friendly, chatty. Drafts answers from context.
-   **`auditor.py` (`gemma3:4b`)**: **The Verifier**. Strict, logical. Checks if the Messenger's draft is supported by the context to prevent hallucinations.

### 4. **Voice Engine (`voice_engine/`)**
A separate microservice running on Port 8001.
-   **`server.py`**: FastAPI app handling heavy AI Audio models.
    -   **TTS**: Uses **Kokoro (ONNX)** for high-quality speech synthesis.
    -   **STT**: Uses **Faster-Whisper** for accurate transcription.
-   **Communication**: `app/services/voice_service.py` proxies requests to this service.

### 5. **Database & Models**
-   **`db/database.py`**: Async SQLAlchemy setup + `sqlite-vec` extension loading.
-   **`models/base.py`**:
    -   `Note`: The central entity. Has `parent_id` (hierarchy) and `is_hidden` (visibility).
    -   `Summary`: Stores the Rolling Update state.

---

## Independent Testing Guide

### Prerequisites
1.  Ensure Backend is running:
    ```bash
    cd backend
    source .venv/bin/activate
    uvicorn app.main:app --reload
    ```
2.  Ensure Voice Engine is running:
    ```bash
    # New Terminal
    sh start_voice_engine.sh
    # OR
    cd voice_engine && source .venv/bin/activate && python server.py
    ```
3.  Ensure Ollama is running (`ollama serve`).

### Test 1: Vector Search (API)
**Function**: `GET /api/search`
**Test**:
```bash
curl "http://localhost:8000/api/search?q=gemma"
```
*Expected*: Returns JSON list of notes with `distance` scores.

### Test 2: Agentic Chat (API)
**Function**: `POST /api/chat/pdf/{id}`
**Test**:
1.  Upload a PDF via UI (or curl). Note the `id` (e.g., `8`).
2.  Run:
    ```bash
    curl -X POST "http://localhost:8000/api/chat/pdf/8" \
         -H "Content-Type: application/json" \
         -d '{"query": "What is this document about?"}'
    ```
*Expected*:
```json
{
  "answer": "This document covers...",
  "verified": true,
  "correction": null
}
```
