"""Клиент Google Books API для поиска книг (ТЗ 4.3.2)."""

import logging
from typing import Any

import httpx

from app.core.config import settings
from app.core.constants import ITEM_BOOK, SOURCE_GOOGLE_BOOKS
from app.services.providers.base import ExternalItem

logger = logging.getLogger(__name__)


def _parse_year(date_str: str | None) -> int | None:
    if not date_str or len(date_str) < 4:
        return None
    try:
        return int(date_str[:4])
    except ValueError:
        return None


def _format_thumbnail(image_links: dict[str, str] | None) -> str | None:
    if not image_links:
        return None
    url = image_links.get("thumbnail") or image_links.get("smallThumbnail")
    if not url:
        return None
    return url.replace("http://", "https://")


class GoogleBooksProvider:
    """Асинхронный поиск книг в Google Books API."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def search_books(self, query: str) -> list[ExternalItem]:
        if not query.strip():
            return []

        url = f"{settings.google_books_base_url.rstrip('/')}/volumes"
        params: dict[str, Any] = {
            "q": query.strip(),
            "maxResults": 10,
        }
        if settings.google_books_api_key:
            params["key"] = settings.google_books_api_key

        data = await self._get(url, params)
        items_raw = data.get("items", []) if data else []

        items: list[ExternalItem] = []
        for raw in items_raw:
            book_id = raw.get("id")
            vinfo = raw.get("volumeInfo", {})
            title = vinfo.get("title")
            if not book_id or not title:
                continue

            categories = vinfo.get("categories", [])
            genres = [cat.lower() for cat in categories if isinstance(cat, str)]

            language = vinfo.get("language")
            country = language.upper() if language else None

            items.append(
                ExternalItem(
                    type=ITEM_BOOK,
                    source=SOURCE_GOOGLE_BOOKS,
                    external_id=str(book_id),
                    title=title,
                    original_title=None,
                    year=_parse_year(vinfo.get("publishedDate")),
                    country=country,
                    genres=genres,
                    description=vinfo.get("description"),
                    poster_path=_format_thumbnail(vinfo.get("imageLinks")),
                )
            )
        return items

    async def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any] | None:
        try:
            if self._client:
                resp = await self._client.get(
                    url, params=params, timeout=settings.external_timeout_seconds
                )
                resp.raise_for_status()
                return resp.json()

            async with httpx.AsyncClient(timeout=settings.external_timeout_seconds) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as exc:
            logger.warning("Ошибка запроса к Google Books (%s): %s", url, exc)
            return None
