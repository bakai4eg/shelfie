"""Служба интеграции и кэширования внешних карточек (ТЗ 4.3.2).

Получает фильмы и сериалы из TMDB, книги из OpenLibrary и Google Books,
кэширует в собственной БД на CACHE_TTL_DAYS (по умолчанию 7 дней) и дедуплицирует
по уникальному ключу (source, external_id).
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import (
    ITEM_BOOK,
    ITEM_MOVIE,
    ITEM_SERIES,
    MODERATION_APPROVED,
    SOURCE_LOCAL,
)
from app.models.catalog import CatalogItem
from app.services.providers import (
    ExternalItem,
    GoogleBooksProvider,
    OpenLibraryProvider,
    TMDBProvider,
)

logger = logging.getLogger(__name__)


async def fetch_from_external_providers(
    query: str,
    item_type: str | None = None,
    *,
    tmdb: TMDBProvider | None = None,
    openlibrary: OpenLibraryProvider | None = None,
    google_books: GoogleBooksProvider | None = None,
) -> list[ExternalItem]:
    """Параллельно опрашивает внешние сервисы с защитой от таймаутов и сбоев."""
    clean_q = query.strip()
    if len(clean_q) < 2:
        return []

    tmdb_client = tmdb or TMDBProvider()
    ol_client = openlibrary or OpenLibraryProvider()
    gb_client = google_books or GoogleBooksProvider()

    tasks = []
    if item_type == ITEM_MOVIE:
        tasks.append(tmdb_client.search_movies(clean_q))
    elif item_type == ITEM_SERIES:
        tasks.append(tmdb_client.search_series(clean_q))
    elif item_type == ITEM_BOOK:
        tasks.append(ol_client.search_books(clean_q))
        tasks.append(gb_client.search_books(clean_q))
    else:
        # Без фильтра по типу — опрашиваем все источники
        tasks.append(tmdb_client.search_movies(clean_q))
        tasks.append(tmdb_client.search_series(clean_q))
        tasks.append(ol_client.search_books(clean_q))
        tasks.append(gb_client.search_books(clean_q))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    items: list[ExternalItem] = []
    for res in results:
        if isinstance(res, Exception):
            logger.warning("Сбой одного из внешних источников при поиске %r: %s", clean_q, res)
            continue
        items.extend(res)

    return items


async def sync_external_catalog(
    db: AsyncSession,
    query: str,
    item_type: str | None = None,
    *,
    tmdb: TMDBProvider | None = None,
    openlibrary: OpenLibraryProvider | None = None,
    google_books: GoogleBooksProvider | None = None,
) -> int:
    """Проверяет кэш в БД. Если данных нет или кэш устарел — запрашивает внешние API и сохраняет."""
    clean_q = query.strip().lower()
    if len(clean_q) < 2:
        return 0

    now = datetime.now(UTC)
    ttl_cutoff = now - timedelta(days=settings.cache_ttl_days)

    # Проверяем, есть ли уже свежие внешние карточки по этому запросу
    cache_check = select(func.count(CatalogItem.id)).where(
        CatalogItem.source != SOURCE_LOCAL,
        CatalogItem.title_normalized.like(f"%{clean_q}%"),
        CatalogItem.fetched_at >= ttl_cutoff,
    )
    if item_type:
        cache_check = cache_check.where(CatalogItem.type == item_type)

    cached_count = (await db.scalar(cache_check)) or 0
    if cached_count > 0:
        # Кэш свежий, внешние API не опрашиваем
        return 0

    # Запрашиваем внешние сервисы
    external_items = await fetch_from_external_providers(
        clean_q,
        item_type,
        tmdb=tmdb,
        openlibrary=openlibrary,
        google_books=google_books,
    )
    if not external_items:
        return 0

    saved_count = 0
    for ext in external_items:
        # Дедупликация по (source, external_id)
        stmt = select(CatalogItem).where(
            CatalogItem.source == ext.source,
            CatalogItem.external_id == ext.external_id,
        )
        existing = await db.scalar(stmt)

        if existing:
            # Обновляем устаревшие данные карточки
            existing.title = ext.title
            existing.original_title = ext.original_title
            existing.year = ext.year or existing.year
            existing.country = ext.country or existing.country
            if ext.genres:
                existing.genres = ext.genres
            if ext.description:
                existing.description = ext.description
            if ext.poster_path:
                existing.poster_path = ext.poster_path
            existing.fetched_at = now
            existing.title_normalized = (
                f"{ext.title} {ext.original_title or ''}".strip().lower()
            )
            saved_count += 1
        else:
            # Создаём новую карточку с флагом approved
            new_item = CatalogItem(
                type=ext.type,
                source=ext.source,
                external_id=ext.external_id,
                title=ext.title,
                original_title=ext.original_title,
                title_normalized=f"{ext.title} {ext.original_title or ''}".strip().lower(),
                year=ext.year,
                country=ext.country,
                genres=ext.genres,
                description=ext.description,
                poster_path=ext.poster_path,
                is_local=False,
                moderation_status=MODERATION_APPROVED,
                fetched_at=now,
            )
            db.add(new_item)
            saved_count += 1

    try:
        await db.commit()
    except Exception as exc:
        logger.warning("Ошибка при сохранении внешних карточек в БД: %s", exc)
        await db.rollback()

    return saved_count


async def refresh_item_if_stale(db: AsyncSession, item: CatalogItem) -> CatalogItem:
    """Обновляет устаревшую карточку внешнего источника при прямом обращении (ТЗ 4.3.2)."""
    if item.source == SOURCE_LOCAL or not item.title:
        return item
    if not settings.enable_external_providers:
        return item

    now = datetime.now(UTC)
    ttl_cutoff = now - timedelta(days=settings.cache_ttl_days)
    fetched_at = item.fetched_at
    if fetched_at and fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=UTC)

    if fetched_at and fetched_at >= ttl_cutoff:
        return item

    try:
        await sync_external_catalog(db, item.title, item.type)
        await db.refresh(item)
    except Exception:
        pass  # если источник недоступен, отдаем существующие данные из БД

    return item

