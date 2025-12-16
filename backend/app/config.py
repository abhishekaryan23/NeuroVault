from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "NeuroVault"
    DATABASE_URL: str = "sqlite+aiosqlite:///./neurovault.db"
    
    # Path to store uploaded files
    UPLOAD_DIR: str = "dumps"
    
    # AI Models (Ollama)
    EMBEDDING_MODEL: str = "embeddinggemma"
    SUMMARY_MODEL: str = "gemma3:4b"
    IMAGE_MODEL: str = "gemma3:4b"
    AUDITOR_MODEL: str = "gemma3:4b"
    MESSENGER_MODEL: str = "gemma3:4b"

    # LLM Provider Config
    LLM_PROVIDER: str = "ollama"
    LLM_API_BASE: str = "http://localhost:11434"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
