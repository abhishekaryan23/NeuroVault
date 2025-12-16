from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings
from db.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    pass

from app.api import notes, upload, summary
from app.api import notes, summary, upload, chat
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Open-GDR Backend", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(notes.router, prefix="/api", tags=["notes"])
app.include_router(summary.router, prefix="/api", tags=["summary"])
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
from app.api import voice, image
app.include_router(voice.router, prefix="/api", tags=["voice"])
app.include_router(image.router, prefix="/api/image", tags=["image"])

from fastapi.staticfiles import StaticFiles
import os
os.makedirs("dumps", exist_ok=True)
app.mount("/files", StaticFiles(directory="dumps"), name="files")

@app.get("/health")
def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
