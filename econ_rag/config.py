"""Configuration for the economics RAG system."""

from pathlib import Path
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Runtime settings, overridable via environment variables or .env."""

    DATABASE_URL: str = f"sqlite:///{PROJECT_ROOT / 'econ_rag.db'}"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8100

    # Chunking is word-based; 512 tokens is roughly 380 words.
    CHUNK_SIZE: int = 380
    CHUNK_OVERLAP: int = 60

    RAG_TOP_K: int = 5

    LECTURE_DIR: str = str(PROJECT_ROOT / "data" / "lectures")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
