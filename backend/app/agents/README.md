# Agents Documentation

Autonomous entities for higher-level reasoning.

## Files & Classes

### `base.py`
**Class `BaseAgent`**
- Wrapper around `ollama.chat`.
- Manages System Prompt and Context concatenation.

### `messenger.py`
**Class `MessengerAgent` (The Generator)**
- **Model**: `gemma3n:e4b` (Fast, optimized for chat).
- **Role**: User Interface.
- **Method `answer_with_rag(query, context_chunks)`**:
    - Formats chunks into a context block.
    - Generates a friendly, concise answer.

### `auditor.py`
**Class `AuditorAgent` (The Verifier)**
- **Model**: `gemma3:4b` (Smart, optimized for logic).
- **Role**: Quality Control / Hallucination Check.
- **Method `verify(question, answer, context_chunks)`**:
    - **Input**: The original question, the Messenger's draft answer, and the source context.
    - **Logic**: Asks "Is this answer completely supported by the context?".
    - **Output**: JSON `{ is_valid: bool, correction: str | null }`.
