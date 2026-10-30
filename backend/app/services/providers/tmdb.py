"""Клиент TMDB (The Movie Database) для фильмов и сериалов (ТЗ 4.3.2)."""

import logging
from typing import Any

import httpx

from app.core.config import settings
from app.core.constants import ITEM_MOVIE, ITEM_SERIES, SOURCE_TMDB
from app.services.providers.base import ExternalItem

logger = logging.getLogger(__name__)

TMDB_GENRES = {
    28: "боевик",
    12: "приключения",
    16: "мультфильм",
    35: "комедия",
    80: "криминал",
    99: "документальный",
    18: "драма",
    10751: "семейный",
    14: "фэнтези",
    36: "история",
    27: "ужасы",
    10402: "музыка",
    9648: "детектив",
    10749: "мелодрама",
    878: "фантастика",
    10770: "телефильм",
    53: "триллер",
    10752: "военный",
    37: "вестерн",
    10759: "боевик и приключения",
    10762: "детский",
    10765: "фантастика и фэнтези",
}


def _parse_year(date_str: str | None) -> int | None:
    if not date_str or len(date_str) < 4:
        return None
    try:
        return int(date_str[:4])
    except ValueError:
        return None


def _format_poster(poster_path: str | None) -> str | None:
    if not poster_path:
        return None
    if poster_path.startswith("http"):
        return poster_path
    return f"https://image.tmdb.org/t/p/w500{poster_path}"


def _map_genres(genre_ids: list[int] | None) -> list[str]:
    if not genre_ids:
        return []
    return [TMDB_GENRES[gid] for gid in genre_ids if gid in TMDB_GENRES]


class TMDBProvider:
    """Асинхронный поиск фильмов и сериалов в TMDB."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def search_movies(self, query: str) -> list[ExternalItem]:
        if not settings.tmdb_api_key or not query.strip():
            return []

        url = f"{settings.tmdb_base_url.rstrip('/')}/search/movie"
        params: dict[str, Any] = {
            "api_key": settings.tmdb_api_key,
            "query": query.strip(),
            "language": "ru-RU",
        }
        data = await self._get(url, params)
        results = data.get("results", []) if data else []

        items: list[ExternalItem] = []
        for r in results:
            item_id = str(r.get("id"))
            title = r.get("title") or r.get("original_title") or ""
            if not title:
                continue
            items.append(
                ExternalItem(
                    type=ITEM_MOVIE,
                    source=SOURCE_TMDB,
                    external_id=item_id,
                    title=title,
                    original_title=r.get("original_title"),
                    year=_parse_year(r.get("release_date")),
                    country=(
                        r.get("original_language", "").upper()
                        if r.get("original_language")
                        else None
                    ),
                    genres=_map_genres(r.get("genre_ids")),
                    description=r.get("overview") or None,
                    poster_path=_format_poster(r.get("poster_path")),
                )
            )
        return items

    async def search_series(self, query: str) -> list[ExternalItem]:
        if not settings.tmdb_api_key or not query.strip():
            return []

        url = f"{settings.tmdb_base_url.rstrip('/')}/search/tv"
        params: dict[str, Any] = {
            "api_key": settings.tmdb_api_key,
            "query": query.strip(),
            "language": "ru-RU",
        }
        data = await self._get(url, params)
        results = data.get("results", []) if data else []

        items: list[ExternalItem] = []
        for r in results:
            item_id = str(r.get("id"))
            title = r.get("name") or r.get("original_name") or ""
            if not title:
                continue
            origin_country = r.get("origin_country", [])
            country = origin_country[0] if origin_country else None
            items.append(
                ExternalItem(
                    type=ITEM_SERIES,
                    source=SOURCE_TMDB,
                    external_id=item_id,
                    title=title,
                    original_title=r.get("original_name"),
                    year=_parse_year(r.get("first_air_date")),
                    country=country,
                    genres=_map_genres(r.get("genre_ids")),
                    description=r.get("overview") or None,
                    poster_path=_format_poster(r.get("poster_path")),
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
            logger.warning("Ошибка запроса к TMDB (%s): %s", url, exc)
            return None
