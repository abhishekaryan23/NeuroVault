import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.main import app
from db.database import get_db, Base
from app.core.llm import NeuroVaultLLM
from unittest.mock import AsyncMock

# In-memory SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="function")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(engine):
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session

@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    
    # Mock LLM to avoid costs/latency
    NeuroVaultLLM.chat = AsyncMock(return_value={
        "message": {"content": '{"intent": "CHAT", "response": "Mocked Response"}'}
    })
    NeuroVaultLLM.generate = AsyncMock(return_value={"response": "Mocked Summary"})
    
    # Mock Voice Service Transcribe/Synthesize to avoid loading heavy models
    from app.services.voice_service import VoiceService
    VoiceService.transcribe = AsyncMock(return_value="Mocked Transcription")
    VoiceService.synthesize_audio = AsyncMock(return_value=None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    
    app.dependency_overrides.clear()
