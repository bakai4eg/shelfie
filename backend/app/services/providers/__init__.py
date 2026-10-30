"""Провайдеры внешних данных для каталога."""

from app.services.providers.base import ExternalItem
from app.services.providers.google_books import GoogleBooksProvider
from app.services.providers.openlibrary import OpenLibraryProvider
from app.services.providers.tmdb import TMDBProvider

__all__ = [
    "ExternalItem",
    "GoogleBooksProvider",
    "OpenLibraryProvider",
    "TMDBProvider",
]
