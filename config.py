"""Pydantic settings for Tarot Agent."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.

    All settings can be overridden via .env file or environment variables.
    """

    # LLM
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5-20250929"
    EXTRACTION_MODEL: str = "claude-haiku-4-5-20251001"
    LLM_TIMEOUT_SECONDS: int = 60

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_ANON_KEY: str = ""

    # Embeddings
    OPENAI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536

    # Features
    RAG_ENABLED: bool = True
    SEMANTIC_MEMORY_ENABLED: bool = False
    CUSTOM_DECKS_ENABLED: bool = False

    # Reading defaults
    DEFAULT_MODE: str = "intuitive"
    DEFAULT_REVERSAL_PROBABILITY: float = 0.3
    MEMORY_EXTRACTION_MIN_MESSAGES: int = 4

    # Infrastructure
    SENTRY_DSN: str | None = None
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
