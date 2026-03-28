from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, loaded from environment variables."""

    DATABASE_URL: str = "sqlite+aiosqlite:///./uply.db"


settings = Settings()
