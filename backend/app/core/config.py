"""Настройки приложения. Читаются из переменных окружения / .env."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # общее
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "dev-only-secret-key-change-me-in-production"
    access_token_expire_minutes: int = 60 * 24
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # база данных
    database_url: str = "sqlite+aiosqlite:///./shelfie.sqlite3"

    # внешние источники
    tmdb_api_key: str = ""
    tmdb_base_url: str = "https://api.themoviedb.org/3"
    openlibrary_base_url: str = "https://openlibrary.org"
    google_books_api_key: str = ""
    google_books_base_url: str = "https://www.googleapis.com/books/v1"
    cache_ttl_days: int = 7
    external_timeout_seconds: int = 8

    # файлы
    media_root: str = "media"
    max_upload_size_mb: int = 5

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
