from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, loaded from environment variables."""

    DATABASE_URL: str = "sqlite+aiosqlite:///./uply.db"
    CHECK_INTERVAL_SECONDS: int = 60
    DEFAULT_TIMEOUT_SECONDS: int = 10


settings = Settings()
