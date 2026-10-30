"""Базовая модель элемента из внешнего источника."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class ExternalItem:
    """Унифицированное представление карточки из внешнего API (TMDB, OpenLibrary, Google Books)."""

    type: str  # book, movie, series
    source: str  # tmdb, openlibrary, google_books
    external_id: str
    title: str
    original_title: str | None = None
    year: int | None = None
    country: str | None = None
    genres: list[str] = field(default_factory=list)
    description: str | None = None
    poster_path: str | None = None
