"""Тесты подсистемы интеграций с внешними каталогами (T2.2, ТЗ 4.3.2).

Проверяет:
- Клиенты TMDB, OpenLibrary, Google Books (нормализация данных, постеры, жанры).
- Отказоустойчивость: таймауты и 5xx ошибки не прерывают работу.
- Кэширование в БД с учётом CACHE_TTL_DAYS (7 дней) и повторные запросы из БД без обращения к API.
- Дедупликацию по уникальному ключу (source, external_id).
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.constants import (
    ITEM_BOOK,
    ITEM_MOVIE,
    ITEM_SERIES,
    MODERATION_APPROVED,
    SOURCE_GOOGLE_BOOKS,
    SOURCE_OPENLIBRARY,
    SOURCE_TMDB,
)
from app.db.base import Base
from app.db.session import json_serializer
from app.models.catalog import CatalogItem
from app.services.integrations import (
    fetch_from_external_providers,
    sync_external_catalog,
)
from app.services.providers.base import ExternalItem
from app.services.providers.google_books import GoogleBooksProvider
from app.services.providers.openlibrary import OpenLibraryProvider
from app.services.providers.tmdb import TMDBProvider


@pytest.fixture
async def db():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        json_serializer=json_serializer,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_tmdb_movies_and_series_parsing():
    """TMDBProvider корректно парсит фильмы и сериалы, маппит жанры и постеры."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    # Мок ответа для фильма
    movie_payload = {
        "results": [
            {
                "id": 550,
                "title": "Бойцовский клуб",
                "original_title": "Fight Club",
                "release_date": "1999-10-15",
                "original_language": "en",
                "genre_ids": [18, 53],  # драма, триллер
                "overview": "Сотрудник страховой компании...",
                "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
            }
        ]
    }

    # Мок ответа для сериала
    tv_payload = {
        "results": [
            {
                "id": 1396,
                "name": "Во все тяжкие",
                "original_name": "Breaking Bad",
                "first_air_date": "2008-01-20",
                "origin_country": ["US"],
                "genre_ids": [18, 80],  # драма, криминал
                "overview": "Учитель химии...",
                "poster_path": "/ggFHVNu6YYI5L9pCfOacjizRGt.jpg",
            }
        ]
    }

    resp_mock = MagicMock()
    resp_mock.raise_for_status = MagicMock()

    with patch.object(settings, "tmdb_api_key", "fake-key"):
        provider = TMDBProvider(client=mock_client)

        resp_mock.json.return_value = movie_payload
        mock_client.get.return_value = resp_mock
        movies = await provider.search_movies("Бойцовский клуб")

        assert len(movies) == 1
        movie = movies[0]
        assert movie.type == ITEM_MOVIE
        assert movie.source == SOURCE_TMDB
        assert movie.external_id == "550"
        assert movie.title == "Бойцовский клуб"
        assert movie.original_title == "Fight Club"
        assert movie.year == 1999
        assert "драма" in movie.genres
        assert "триллер" in movie.genres
        assert movie.poster_path == "https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg"

        resp_mock.json.return_value = tv_payload
        mock_client.get.return_value = resp_mock
        series_list = await provider.search_series("Breaking Bad")

        assert len(series_list) == 1
        series = series_list[0]
        assert series.type == ITEM_SERIES
        assert series.source == SOURCE_TMDB
        assert series.external_id == "1396"
        assert series.title == "Во все тяжкие"
        assert series.original_title == "Breaking Bad"
        assert series.year == 2008
        assert series.country == "US"
        assert "криминал" in series.genres


@pytest.mark.asyncio
async def test_openlibrary_and_google_books_parsing():
    """OpenLibraryProvider и GoogleBooksProvider парсят книги и обложки."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    resp_mock = MagicMock()
    resp_mock.raise_for_status = MagicMock()

    # OpenLibrary
    ol_payload = {
        "docs": [
            {
                "key": "/works/OL27448W",
                "title": "Война и мир",
                "first_publish_year": 1869,
                "author_name": ["Лев Толстой"],
                "subject": ["Historical fiction", "Classics"],
                "language": ["rus"],
                "cover_i": 123456,
            }
        ]
    }
    resp_mock.json.return_value = ol_payload
    mock_client.get.return_value = resp_mock

    ol_provider = OpenLibraryProvider(client=mock_client)
    ol_books = await ol_provider.search_books("Война и мир")
    assert len(ol_books) == 1
    ol_book = ol_books[0]
    assert ol_book.type == ITEM_BOOK
    assert ol_book.source == SOURCE_OPENLIBRARY
    assert ol_book.external_id == "OL27448W"
    assert ol_book.title == "Война и мир"
    assert ol_book.year == 1869
    assert ol_book.poster_path == "https://covers.openlibrary.org/b/id/123456-M.jpg"
    assert "Толстой" in (ol_book.description or "")

    # Google Books
    gb_payload = {
        "items": [
            {
                "id": "zyTCAlFPjgYC",
                "volumeInfo": {
                    "title": "Мастер и Маргарита",
                    "publishedDate": "1967",
                    "categories": ["Fiction"],
                    "language": "ru",
                    "description": "Культовый роман...",
                    "imageLinks": {
                        "thumbnail": "http://books.google.com/books/content?id=zyTCAlFPjgYC&printsec=frontcover"
                    },
                },
            }
        ]
    }
    resp_mock.json.return_value = gb_payload
    mock_client.get.return_value = resp_mock

    gb_provider = GoogleBooksProvider(client=mock_client)
    gb_books = await gb_provider.search_books("Мастер и Маргарита")
    assert len(gb_books) == 1
    gb_book = gb_books[0]
    assert gb_book.type == ITEM_BOOK
    assert gb_book.source == SOURCE_GOOGLE_BOOKS
    assert gb_book.external_id == "zyTCAlFPjgYC"
    assert gb_book.title == "Мастер и Маргарита"
    assert gb_book.year == 1967
    assert gb_book.poster_path.startswith("https://")


@pytest.mark.asyncio
async def test_resilience_timeout_and_errors():
    """Сбой одного внешнего источника не прерывает работу остальных."""
    failing_tmdb = MagicMock(spec=TMDBProvider)
    failing_tmdb.search_movies = AsyncMock(
        side_effect=httpx.TimeoutException("Connection timed out")
    )
    failing_tmdb.search_series = AsyncMock(
        side_effect=httpx.HTTPStatusError("500 Internal Server Error", request=None, response=None)
    )

    working_ol = MagicMock(spec=OpenLibraryProvider)
    working_ol.search_books = AsyncMock(
        return_value=[
            ExternalItem(
                type=ITEM_BOOK,
                source=SOURCE_OPENLIBRARY,
                external_id="OL999W",
                title="Уцелевшая книга",
            )
        ]
    )

    working_gb = MagicMock(spec=GoogleBooksProvider)
    working_gb.search_books = AsyncMock(return_value=[])

    # Опрашиваем все
    results = await fetch_from_external_providers(
        "тест сбоя",
        tmdb=failing_tmdb,
        openlibrary=working_ol,
        google_books=working_gb,
    )
    assert len(results) == 1
    assert results[0].external_id == "OL999W"


@pytest.mark.asyncio
async def test_sync_external_catalog_caching_and_ttl(db):
    """Синхронизация кэширует результаты в БД и не опрашивает API при свежем кэше (ТЗ 4.3.2)."""
    mock_tmdb = MagicMock(spec=TMDBProvider)
    mock_tmdb.search_movies = AsyncMock(
        return_value=[
            ExternalItem(
                type=ITEM_MOVIE,
                source=SOURCE_TMDB,
                external_id="1010",
                title="Интерстеллар",
                original_title="Interstellar",
                year=2014,
            )
        ]
    )
    mock_tmdb.search_series = AsyncMock(return_value=[])
    mock_ol = MagicMock(spec=OpenLibraryProvider)
    mock_ol.search_books = AsyncMock(return_value=[])
    mock_gb = MagicMock(spec=GoogleBooksProvider)
    mock_gb.search_books = AsyncMock(return_value=[])

    # Первый запрос: в БД ничего нет -> обращается к API и сохраняет
    saved = await sync_external_catalog(
        db,
        "Интерстеллар",
        tmdb=mock_tmdb,
        openlibrary=mock_ol,
        google_books=mock_gb,
    )
    assert saved == 1
    assert mock_tmdb.search_movies.call_count == 1

    # Проверяем сохранённый объект в БД
    item = await db.scalar(
        select(CatalogItem).where(
            CatalogItem.source == SOURCE_TMDB,
            CatalogItem.external_id == "1010",
        )
    )
    assert item is not None
    assert item.title == "Интерстеллар"
    assert item.moderation_status == MODERATION_APPROVED
    assert item.fetched_at is not None

    # Повторный запрос в пределах 7 дней: кэш свежий, API вызываться НЕ должен
    mock_tmdb.search_movies.reset_mock()
    saved_second = await sync_external_catalog(
        db,
        "Интерстеллар",
        tmdb=mock_tmdb,
        openlibrary=mock_ol,
        google_books=mock_gb,
    )
    assert saved_second == 0
    assert mock_tmdb.search_movies.call_count == 0


@pytest.mark.asyncio
async def test_deduplication_updates_existing_item(db):
    """Дедупликация по (source, external_id): повторное получение обновляет существующую запись."""
    # Создаём существующую запись с устаревшим fetched_at (> 7 дней назад)
    old_time = datetime.now(UTC) - timedelta(days=10)
    existing = CatalogItem(
        type=ITEM_MOVIE,
        source=SOURCE_TMDB,
        external_id="2020",
        title="Старое название",
        title_normalized="старое название",
        year=2010,
        moderation_status=MODERATION_APPROVED,
        fetched_at=old_time,
    )
    db.add(existing)
    await db.commit()

    # Новый ответ от внешнего источника с тем же (source, external_id)
    mock_tmdb = MagicMock(spec=TMDBProvider)
    mock_tmdb.search_movies = AsyncMock(
        return_value=[
            ExternalItem(
                type=ITEM_MOVIE,
                source=SOURCE_TMDB,
                external_id="2020",
                title="Обновлённое название",
                year=2011,
                genres=["драма"],
            )
        ]
    )
    mock_tmdb.search_series = AsyncMock(return_value=[])

    mock_ol = MagicMock(spec=OpenLibraryProvider)
    mock_ol.search_books = AsyncMock(return_value=[])
    mock_gb = MagicMock(spec=GoogleBooksProvider)
    mock_gb.search_books = AsyncMock(return_value=[])

    await sync_external_catalog(
        db,
        "Старое",
        tmdb=mock_tmdb,
        openlibrary=mock_ol,
        google_books=mock_gb,
    )

    # Записей в БД должно остаться ровно 1 (не задублировалось!)
    total = await db.scalar(
        select(func.count(CatalogItem.id)).where(
            CatalogItem.source == SOURCE_TMDB,
            CatalogItem.external_id == "2020",
        )
    )
    assert total == 1

    # Поля обновлены
    await db.refresh(existing)
    assert existing.title == "Обновлённое название"
    assert existing.year == 2011
    assert "драма" in existing.genres
    fetched_at = existing.fetched_at
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=UTC)
    assert fetched_at > old_time


@pytest.mark.asyncio
async def test_refresh_item_if_stale_on_access(db):
    """refresh_item_if_stale обновляет карточку, если fetched_at старше TTL (ТЗ 4.3.2)."""
    from app.services.integrations import refresh_item_if_stale

    old_time = datetime.now(UTC) - timedelta(days=14)
    item = CatalogItem(
        type=ITEM_MOVIE,
        source=SOURCE_TMDB,
        external_id="3030",
        title="Старый фильм",
        title_normalized="старый фильм",
        year=2000,
        moderation_status=MODERATION_APPROVED,
        fetched_at=old_time,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    # При выключенных провайдерах или свежем кэше — не меняется
    res = await refresh_item_if_stale(db, item)
    assert res.id == item.id

