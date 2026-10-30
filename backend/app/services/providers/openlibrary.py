"""Клиент OpenLibrary для поиска книг (ТЗ 4.3.2)."""

import logging
from typing import Any

import httpx

from app.core.config import settings
from app.core.constants import ITEM_BOOK, SOURCE_OPENLIBRARY
from app.services.providers.base import ExternalItem

logger = logging.getLogger(__name__)


def _format_cover(cover_id: int | None) -> str | None:
    if not cover_id:
        return None
    return f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"


class OpenLibraryProvider:
    """Асинхронный поиск книг в OpenLibrary (не требует API-ключа)."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def search_books(self, query: str) -> list[ExternalItem]:
        if not query.strip():
            return []

        url = f"{settings.openlibrary_base_url.rstrip('/')}/search.json"
        params: dict[str, Any] = {
            "q": query.strip(),
            "limit": 10,
        }
        data = await self._get(url, params)
        docs = data.get("docs", []) if data else []

        items: list[ExternalItem] = []
        for doc in docs:
            raw_key = doc.get("key", "")
            work_id = raw_key.replace("/works/", "").strip()
            title = doc.get("title")
            if not work_id or not title:
                continue

            subjects = doc.get("subject", [])
            genres = [s.lower() for s in subjects[:5] if isinstance(s, str)]

            language = doc.get("language", [])
            country = language[0].upper() if language and isinstance(language, list) else None

            author_names = doc.get("author_name", [])
            description = (
                f"Автор: {', '.join(author_names[:3])}" if author_names else None
            )

            items.append(
                ExternalItem(
                    type=ITEM_BOOK,
                    source=SOURCE_OPENLIBRARY,
                    external_id=work_id,
                    title=title,
                    original_title=None,
                    year=doc.get("first_publish_year"),
                    country=country,
                    genres=genres,
                    description=description,
                    poster_path=_format_cover(doc.get("cover_i")),
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
            logger.warning("Ошибка запроса к OpenLibrary (%s): %s", url, exc)
            return None
