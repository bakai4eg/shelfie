"""Схемы каталога. Контракт — docs/api.md, раздел 3."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CatalogType = Literal["book", "movie", "series"]
CatalogSource = Literal["local", "tmdb", "openlibrary", "google_books"]
CatalogSort = Literal["relevance", "year_desc", "rating_desc", "title_asc"]


class CatalogItemRead(BaseModel):
    """Карточка в списке. `poster_path` из БД превращается в `poster_url`."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    type: CatalogType
    source: CatalogSource
    external_id: str | None = None
    title: str
    original_title: str | None = None
    year: int | None = None
    country: str | None = None
    genres: list[str] = Field(default_factory=list)
    description: str | None = None
    poster_url: str | None = Field(default=None, validation_alias="poster_path")
    is_local: bool = False
    rating_avg: float = 0
    ratings_count: int = 0
    created_at: datetime

    @field_validator("poster_url", mode="before")
    @classmethod
    def build_media_url(cls, value: str | None) -> str | None:
        if not value:
            return None
        if value.startswith(("http://", "https://", "/")):
            return value
        return f"/media/{value}"


class CatalogFilters(BaseModel):
    """Значения для панели фильтров: только то, что реально есть в каталоге."""

    types: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    year_min: int | None = None
    year_max: int | None = None
