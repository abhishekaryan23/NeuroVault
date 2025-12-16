import pytest
from httpx import AsyncClient
import asyncio

@pytest.mark.asyncio
async def test_create_text_note(client: AsyncClient):
    """Test creating a simple text note."""
    payload = {
        "content": "Test Note 123",
        "media_type": "text",
        "tags": ["test"]
    }
    response = await client.post("/api/notes", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Test Note 123"
    assert data["id"] is not None

@pytest.mark.asyncio
async def test_get_timeline(client: AsyncClient):
    """Test retrieving the timeline."""
    # Create two notes first
    await client.post("/api/notes", json={"content": "Note A", "media_type": "text"})
    await asyncio.sleep(1.1)
    await client.post("/api/notes", json={"content": "Note B", "media_type": "text"})
    
    response = await client.get("/api/timeline?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    # Check if latest is first (Note B)
    assert data[0]["content"] == "Note B"

@pytest.mark.asyncio
async def test_delete_note(client: AsyncClient):
    """Test deleting a note."""
    # Create
    create_res = await client.post("/api/notes", json={"content": "To Delete", "media_type": "text"})
    note_id = create_res.json()["id"]
    
    # Delete
    del_res = await client.delete(f"/api/notes/{note_id}")
    assert del_res.status_code == 200
    
    # Verify gone
    get_res = await client.get("/api/timeline")
    notes = get_res.json()
    assert not any(n["id"] == note_id for n in notes)
