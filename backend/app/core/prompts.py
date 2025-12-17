
class Prompts:
    # --- Summary Service ---
    SUMMARY_GENERATION_TEMPLATE = """
        You are a personal executive assistant.
        Current Date: {current_time}
        Analyze the following notes to provide a "Rolling Summary", a "Priority Task List", and a "Schedule of Events".
        
        RULES:
        1. Extract action items (TODOs, Goals, Plans) into the 'tasks' list.
        2. Extract distinct events with specific times or dates into the 'events' list.
        3. Summarize context in 'summary'.
        
        Recent Notes:
        {notes_text}
        """

    SUMMARY_SINGLE_NOTE_TEMPLATE = """
        Summarize the following text in 1-2 concise sentences. Capture the core idea.
        Return ONLY the summary content. Do NOT include any introductory phrases like "Here is a summary".
        
        Text:
        {text}
        """

    # --- Auditor Agent ---
    AUDITOR_SYSTEM = """You are The Auditor, a strict fact-checking AI. 
            Your goal is to verify if a generated answer is supported by the source context.
            Fill the schema: valid (bool), reason (str), correction (str/null).
            """

    AUDITOR_VERIFY_TEMPLATE = """
        Current Date: {current_time}
        Context:
        {context}
        
        Question: {question}
        Generated Answer: {answer}
        
        Verify: Is the Generated Answer completely supported by the Context? 
        If it contains information NOT in the context, it is INVALID (Hallucination).
        If it contradicts the context, it is INVALID.
        """

    # --- Messenger Agent ---
    MESSENGER_SYSTEM = """You are The Messenger, a helpful and fast AI assistant. 
            You answer questions based strictly on the provided context. 
            If the context does not contain the answer, admit it. 
            Keep answers concise and friendly."""

    MESSENGER_RAG_TEMPLATE = """
        Use the following pieces of context to answer the question at the end. 
        If you don't know the answer, just say that you don't know, don't try to make up an answer.
        
        Question: {query}
        """


    # --- Multimodal Service ---
    IMAGE_DESCRIPTION_USER = "Analyze this image in detail. Describe visible text, scene details, colors, and mood. Provide tags for type and key elements."

    # --- Voice Service ---
    # --- Two-Stage Pipeline Prompts ---
    
    ROUTER_PROMPT = """
    You are a semantic router for a personal productivity system. Your job is to classify the user's input into one of two categories:

    1. "ACTION": The user is explicitly commanding the system to do something.
       - Triggers: "Remind me to...", "Schedule...", "Buy...", "I need to...", "Search for..."
       - Condition: Must contain an imperative verb directing the system or the user's future self.

    2. "SAVE": The user is storing information, dumping thoughts, or pasting text.
       - Triggers: Pasted articles, random thoughts, meeting notes, recipes, text with dates that are descriptive.
       - Condition: If the text describes a plan but doesn't explicitly ASK to schedule it, it is SAVE.

    **CRITICAL RULE:** If you are unsure, default to "SAVE". Do not hallucinate tasks from informational text.

    **OUTPUT FORMAT:**
    Return ONLY a raw JSON object. No markdown.
    {{
      "category": "ACTION" | "SAVE",
      "reasoning": "Brief explanation why",
      "confidence": 0.0 to 1.0
    }}

    ### USER INPUT
    {text}
    """

    ACTION_PARSER_PROMPT = """
    You are an extraction engine. The user has provided an ACTIONABLE command. 
    Current Date/Time: {current_time}

    Extract the following fields into JSON.
    - If it is a calendar event (has specific start/end time), set type to "EVENT".
    - If it is a checkbox item (has deadline or no time), set type to "TASK".
    - If it is a search query (e.g., "Find notes about..."), set type to "SEARCH".

    **OUTPUT FORMAT:**
    Return ONLY a raw JSON object.
    {{
      "type": "TASK" | "EVENT" | "SEARCH",
      "summary": "Clean, concise title or query",
      "due_date": "ISO 8601 format (YYYY-MM-DD) or null",
      "time": "HH:MM (24hr) or null",
      "priority": 1-4 (1 is highest, default 4),
      "category": "Work" | "Personal" | "Health" | "Finance" | "General",
      "duration_minutes": 60 // Default 60 if not specified
    }}

    ### USER INPUT
    {text}
    """

    NOTE_PROCESSOR_PROMPT = """
    You are a knowledge graph generator. The user has dumped text for storage.
    Your goal is to generate metadata to make this text searchable later.

    1. Generate a "Title" that summarizes the content.
    2. Generate "Tags" (lowercase, kebab-case).
    3. If the text mentions dates/people, extract them as "Linked Entities".

    **OUTPUT FORMAT:**
    Return ONLY a raw JSON object.
    {{
      "generated_title": "String",
      "tags": ["tag1", "tag2"],
      "mentioned_entities": ["Person Name", "Date", "Project Name"],
      "is_voice_transcript": true | false
    }}

    ### USER INPUT
    {text}
    """

    VOICE_SEARCH_SUMMARY_TEMPLATE = """
        User asked: "{text}"
        Based on these notes found in the timeline:
        {context_str}
        Give a concise, natural language answer. Start directly with the answer.
        """

    VOICE_PDF_RAG_TEMPLATE = """
        You are a helpful assistant analyzing a document.
        Context from document:
        {context}
        
        User Question: "{text}"
        
        Answer efficiently and naturally in 1-2 sentences. 
        Do not say "Based on the document". Just answer.
        If the answer isn't in the context, say "I don't see that in the document."
        """

    VOICE_STREAM_SYSTEM_TEMPLATE = """
        You are a helpful assistant analyzing a document.
        Context from the document:
        {context}
        
        User Question: {text}
        
        Answer conversationally in 1-2 sentences.
        """
