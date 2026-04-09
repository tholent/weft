from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./weft.db"
    secret_key: str = "change-me"
    resend_api_key: str = ""
    base_url: str = "http://localhost:5173"
    creator_transfer_deadline_hours: int = 24
    auto_archive_days: int = 30

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
