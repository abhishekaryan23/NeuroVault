import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock
from app.core.llm import NeuroVaultLLM
import json
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_create_event_with_duration(client: AsyncClient):
    """
    Test that 'Meeting for 2 hours' saves duration=120.
    """
    # Mock LLM Response
    mock_response_json = json.dumps({
        "intent": "EVENT",
        "content": "Long Meeting",
        "category": "Work",
        "event_datetime": "2025-12-26T10:00:00",
        "event_duration": 120
    })
    
    NeuroVaultLLM.chat.return_value = {
        "message": {"content": mock_response_json}
    }

    payload = {"text": "Long Meeting tomorrow for 2 hours", "speak": "false"}
    
    # 1. Create Event
    response = await client.post("/api/voice/command", data=payload)
    assert response.status_code == 200
    
    # 2. Verify in Tasks
    tasks_res = await client.get("/api/tasks?include_completed=true")
    tasks = tasks_res.json()
    
    event = next((t for t in tasks if t["content"] == "Long Meeting"), None)
    assert event is not None
    assert event["event_duration"] == 120

@pytest.mark.asyncio
async def test_conflict_detection_nudge(client: AsyncClient):
    """
    Test Conflict:
    1. Create 'Lunch' (12:00 - 13:00)
    2. Try 'Call' (12:30 - 13:30)
    3. Expect 'Warning: Clash with Lunch'
    """
    
    # --- Step 1: Create Lunch ---
    NeuroVaultLLM.chat.return_value = {
        "message": {"content": json.dumps({
            "intent": "EVENT", 
            "content": "Lunch", 
            "event_datetime": "2025-12-27T12:00:00",
            "event_duration": 60 
        })}
    }
    await client.post("/api/voice/command", data={"text": "Lunch at 12", "speak": "false"})
    
    # --- Step 2: Create Conflicting Call ---
    NeuroVaultLLM.chat.return_value = {
        "message": {"content": json.dumps({
            "intent": "EVENT", 
            "content": "Call", 
            "event_datetime": "2025-12-27T12:30:00", # Overlaps!
            "event_duration": 60 
        })}
    }
    
    res = await client.post("/api/voice/command", data={"text": "Call at 12:30", "speak": "false"})
    data = res.json()
    
    # --- Step 3: Verify Nudge ---
    print(f"Response Repr: {repr(data['response'])}")
    
    # Check for the warning
    has_warning = "Warning: You have a clash" in data["response"]
    has_clash = "Clash" in data["response"]
    
    assert has_warning or has_clash, f"Expected warning in response: {data['response']}"
