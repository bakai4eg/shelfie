"""Сиды для локальной разработки (T2.1).

Наполняем каталог карточками, чтобы фронтенд не работал с пустым экраном:
книга, фильм и сериал из внешних источников плюс кыргызские карточки.
Повторный запуск не создаёт дубликатов.

Запуск: python -m app.db.seed
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    ITEM_BOOK,
    ITEM_MOVIE,
    ITEM_SERIES,
    MODERATION_APPROVED,
    SOURCE_LOCAL,
    SOURCE_OPENLIBRARY,
    SOURCE_TMDB,
)
from app.db.session import SessionLocal
from app.models.catalog import CatalogItem

SEED_ITEMS: list[dict] = [
    {
        "type": ITEM_BOOK,
        "source": SOURCE_LOCAL,
        "title": "Джамиля",
        "original_title": "Жамийла",
        "year": 1958,
        "country": "Кыргызстан",
        "genres": ["роман", "классика"],
        "description": "Повесть Чингиза Айтматова о любви и свободе.",
        "is_local": True,
        "moderation_status": MODERATION_APPROVED,
    },
    {
        "type": ITEM_BOOK,
        "source": SOURCE_OPENLIBRARY,
        "external_id": "OL27448W",
        "title": "Война и мир",
        "original_title": "War and Peace",
        "year": 1869,
        "country": "Россия",
        "genres": ["роман", "история"],
        "description": "Роман-эпопея Льва Толстого.",
        "is_local": False,
        "moderation_status": MODERATION_APPROVED,
    },
    {
        "type": ITEM_MOVIE,
        "source": SOURCE_TMDB,
        "external_id": "27205",
        "title": "Начало",
        "original_title": "Inception",
        "year": 2010,
        "country": "США",
        "genres": ["фантастика", "триллер"],
        "description": "Вор проникает в сны, чтобы украсть идею.",
        "is_local": False,
        "moderation_status": MODERATION_APPROVED,
    },
    {
        "type": ITEM_MOVIE,
        "source": SOURCE_LOCAL,
        "title": "Курманжан датка",
        "original_title": "Курманжан датка",
        "year": 2014,
        "country": "Кыргызстан",
        "genres": ["драма", "история"],
        "description": "Историческая драма о правительнице алайских кыргызов.",
        "is_local": True,
        "moderation_status": MODERATION_APPROVED,
    },
    {
        "type": ITEM_SERIES,
        "source": SOURCE_TMDB,
        "external_id": "1396",
        "title": "Во все тяжкие",
        "original_title": "Breaking Bad",
        "year": 2008,
        "country": "США",
        "genres": ["драма", "криминал"],
        "description": "Учитель химии становится наркобароном.",
        "is_local": False,
        "moderation_status": MODERATION_APPROVED,
    },
]


async def _exists(db: AsyncSession, item: dict) -> bool:
    stmt = select(CatalogItem.id).where(
        CatalogItem.title == item["title"],
        CatalogItem.source == item["source"],
    )
    if item.get("external_id"):
        stmt = select(CatalogItem.id).where(
            CatalogItem.source == item["source"],
            CatalogItem.external_id == item["external_id"],
        )
    return await db.scalar(stmt) is not None


async def seed() -> int:
    """Добавляет недостающие карточки и возвращает их количество."""
    added = 0
    async with SessionLocal() as db:
        for item in SEED_ITEMS:
            if await _exists(db, item):
                continue
            db.add(CatalogItem(**item))
            added += 1
        await db.commit()
    return added


def main() -> None:
    added = asyncio.run(seed())
    print(f"Добавлено карточек: {added}")


if __name__ == "__main__":
    main()
