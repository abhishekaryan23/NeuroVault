import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock
from app.core.llm import NeuroVaultLLM
import json

@pytest.mark.asyncio
async def test_text_to_event_creation(client: AsyncClient):
    """
    Test that a text dump like 'Meeting tomorrow' creates both:
    1. A Source Note (Text)
    2. A Task/Event Note (linked)
    """
    # Override Mock for this specific test
    mock_response_json = json.dumps({
        "intent": "EVENT",
        "content": "Meeting with team",
        "category": "Event",
        "event_datetime": "2025-12-25T10:00:00"
    })
    
    NeuroVaultLLM.chat.return_value = {
        "message": {"content": mock_response_json}
    }

    # Simulate "Text Dump" -> Agent
    # Note: We must use a multipart form data manually or use data=...
    # The API expects form fields: text, speak
    payload = {"text": "Meeting tomorrow at 10am", "speak": "false"}
    
    response = await client.post("/api/voice/command", data=payload)
    assert response.status_code == 200
    res_data = response.json()
    
    # Assert Response
    assert "scheduled 'Meeting with team'" in res_data["response"]
    
    # Verify DB Side Effects (Timeline)
    timeline_res = await client.get("/api/timeline?limit=10")
    assert timeline_res.status_code == 200
    notes = timeline_res.json()
    
    # We expect the Source Note (content="Meeting tomorrow at 10am") to be present
    source_notes = [n for n in notes if "Meeting tomorrow" in n["content"]]
    assert len(source_notes) > 0
    source_id = source_notes[0]["id"]
    
    # Verify Task Creation via Tasks API
    # Tasks endpoint returns task notes
    tasks_res = await client.get("/api/tasks?include_completed=true")
    assert tasks_res.status_code == 200
    tasks = tasks_res.json()
    
    # Find the generated event
    generated_events = [t for t in tasks if t["content"] == "Meeting with team"]
    assert len(generated_events) > 0
    event = generated_events[0]
    
    assert event["is_task"] is True
    assert event["category"] == "Event"
    assert event["event_at"] == "2025-12-25T10:00:00"
    assert event["origin_note_id"] == source_id

@pytest.mark.asyncio
async def test_date_hallucination_fix(client: AsyncClient):
    """
    Regression test: Ensure 'Tomorrow' is calculated relative to context,
    NOT fixed to a specific date (mocked via LLM Logic Check).
    
    Since we mock the LLM, we can't test the *actual* LLM output here (that's an integration test).
    But we CAN test that we are sending the correct context string.
    """
    # Reset mock
    NeuroVaultLLM.chat.reset_mock()
    NeuroVaultLLM.chat.return_value = {
        "message": {"content": '{"intent": "CHAT"}'}
    }
    
    await client.post("/api/voice/command", data={"text": "Check date", "speak": "false"})
    
    # Verify call args contained "Today is..."
    call_args = NeuroVaultLLM.chat.call_args
    assert call_args is not None
    messages = call_args[1]["messages"] # kwargs['messages']
    prompt_sent = messages[0]["content"]
    
    from datetime import datetime
    today_str = datetime.now().strftime("%A, %B %d, %Y")
    
    assert f"Today is {today_str}" in prompt_sent
