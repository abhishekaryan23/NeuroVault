# Components Documentation

React UI components in `src/components`.

## Files

### `NoteCard.tsx`
The primary display component.
- **Props**: `note: NoteResponse`.
- **Key Logic**:
    - **Truncation**: If `summary` exists, show it + "Read full". If not, but content > 500 chars, truncate + "Read more".
    - **Media Handling**: Renders specific icons/actions based on `media_type`.
    - **Chat Integration**: If `media_type == 'pdf'`, renders the `ChatBubbleLeftRightIcon` which opens `AgentChatModal`.

### `AgentChatModal.tsx`
The Chat Interface for PDFs.
- **Props**: `isOpen`, `noteId`, `title`.
- **State**:
    - `messages`: Array of chat history.
    - `status`: `idle` | `thinking` | `verifying`.
- **Logic**:
    - Calls `chatWithPdfApiChatPdfNoteIdPost` on send.
    - Displays "Thinking & Verifying..." during backend processing.
    - Renders a "Verified by Auditor" badge (Shield Icon) if backend returns `verified: true`.

### `TodoList.tsx`
The Agenda and Task Management UI.
- **Features**:
    - Displays categorized tasks (Urgent, Work, etc.).
    - Separates Events from Tasks.
    - Allows toggling completion status.
    - Polls backend for updates.

### `ThinkingSpace.tsx`
The Visualization Tab.
- **Features**:
    - masonry grid layout for images.
    - Search functionality for visual memories.
    - Image detail modal.

### `VoiceAgent.tsx`
The Global Voice Widget.
- **Features**:
    - Floating microphone button.
    - Handles recording and communication with `voice_engine`.
    - Handles TTS playback.

### `VoiceSearchModal.tsx`
The Interface for Voice Mode.
- **Features**:
    - Visual Orb animation (Listening/Thinking/Speaking).
    - Session context management.

### `NoteInput.tsx`
The "Omnibar" for creating content.
- **Features**:
    - **Text**: Standard notes.
    - **File Drop**: Detects PDF/Image/Audio.
    - **Paste**: Handles pasted content.
