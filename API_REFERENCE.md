# NeuroVault API Reference (Alpha)

Base URL: `http://localhost:8000/api`

## 🧠 Notes & Memories (`/api/notes`)

Core CRUD operations for the memory bank.

- **GET `/notes`**
    - **Query Params**: `limit` (int, default 50), `skip` (int), `search` (str, optional)
    - **Description**: Fetch timeline of notes.
- **POST `/notes`**
    - **Body**: `{ "content": "str", "media_type": "text|image|voice", "tags": [] }`
    - **Description**: Create a new note.
- **GET `/notes/{id}`**
    - **Description**: Get specific note details.
- **DELETE `/notes/{id}`**
    - **Description**: Delete a note.
- **POST `/notes/search`**
    - **Body**: `{ "query": "str", "limit": 5, "start_date": "ISO", "end_date": "ISO" }`
    - **Description**: Hybrid Search (Vector + Keyword) over notes.

## ✅ Tasks & Agenda (`/api/tasks`)

Task management and scheduling.

- **GET `/tasks`**
    - **Query Params**: `include_completed` (bool)
    - **Description**: Get simplified list of tasks/events for the Agenda.
- **POST `/tasks/{id}/toggle`**
    - **Description**: Toggle completion status of a task.

## 🎙️ Voice & Audio (`/api/voice`)

Voice command processing and text-to-speech.

- **POST `/voice/command`**
    - **Body**: Multipart Form Data -> `file` (Audio blob)
    - **Description**: Analyzes intent (Note, Task, Event, Search, Chat).
    - **Returns**: `{ "intent": "...", "response": "...", "audio": "Base64..." }`
- **POST `/voice/tts`**
    - **Body**: `{ "text": "str" }`
    - **Description**: Synthesize speech using Kokoro engine.

## 📄 Upload & Documents (`/api/upload`)

File handling.

- **POST `/upload`**
    - **Body**: Multipart Form Data -> `file`
    - **Description**: Upload Image, PDF, or Audio. Auto-triggers processing (OCR, Transcription, PDF Chunking).

## 💬 Chat & RAG (`/api/chat`)

Dual-Agent (Messenger + Auditor) chat system.

- **POST `/chat/pdf/{note_id}/stream`**
    - **Body**: `{ "query": "str" }`
    - **Description**: Server-Sent Events (SSE) stream answering questions about a specific document.

## 📝 Summaries (`/api/summary`)

- **GET `/summary/daily`**
    - **Description**: Get the latest "Rolling Summary" of user context.
- **POST `/summary/generate`**
    - **Description**: Force regeneration of the summary.
