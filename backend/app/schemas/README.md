# Helper Classes Documentation

Utility schemas and helpers.

## Files

### `schemas/note.py`
Pydantic models for Note operations.
- **`NoteCreate`**:
    - `content`, `media_type`, `tags`.
    - **New**: `parent_id` (for child chunks), `is_hidden` (visibility).
- **`NoteResponse`**: Standard API response format.

### `schemas/timeline.py`
- **`SummaryResponse`**:
    - `summary_text`: The narrative.
    - `tasks`: List of `TaskItem` (task, priority, timeline).
