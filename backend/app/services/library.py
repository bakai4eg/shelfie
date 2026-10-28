"""Сервис полок и оценок (ТЗ 4.2.2, 4.4.1, 4.4.2)."""

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalog import CatalogItem
from app.models.library import Rating, ShelfEntry
from app.models.user import User
from app.schemas.library import RatingResult, ShelfEntryRead, ShelfUpsert
from app.services.catalog import visibility_clause


async def get_visible_item(
    db: AsyncSession, item_id: int, user: User | None
) -> CatalogItem | None:
    stmt = (
        select(CatalogItem)
        .where(
            CatalogItem.id == item_id,
            visibility_clause(user),
        )
    )
    return await db.scalar(stmt)


async def list_shelf(
    db: AsyncSession,
    user: User,
    *,
    status_filter: str | None = None,
    item_type: str | None = None,
    sort: str = "added_desc",
) -> list[ShelfEntryRead]:
    stmt = (
        select(ShelfEntry, Rating.value)
        .join(CatalogItem, CatalogItem.id == ShelfEntry.item_id)
        .outerjoin(
            Rating,
            (Rating.user_id == user.id) & (Rating.item_id == ShelfEntry.item_id),
        )
        .where(
            ShelfEntry.user_id == user.id,
            visibility_clause(user),
        )
        .options(selectinload(ShelfEntry.item))
    )

    if status_filter:
        stmt = stmt.where(ShelfEntry.status == status_filter)
    if item_type:
        stmt = stmt.where(CatalogItem.type == item_type)

    if sort == "rating_desc":
        stmt = stmt.order_by(
            func.coalesce(Rating.value, -1).desc(),
            CatalogItem.rating_avg.desc(),
            ShelfEntry.id.desc(),
        )
    elif sort == "title_asc":
        stmt = stmt.order_by(CatalogItem.title_normalized.asc(), ShelfEntry.id.asc())
    else:
        stmt = stmt.order_by(ShelfEntry.created_at.desc(), ShelfEntry.id.desc())

    rows = (await db.execute(stmt)).all()
    result = []
    for entry, user_rating in rows:
        result.append(
            ShelfEntryRead(
                id=entry.id,
                item_id=entry.item_id,
                status=entry.status,
                finished_at=entry.finished_at,
                item=entry.item,
                user_rating=user_rating,
                created_at=entry.created_at,
                updated_at=entry.updated_at,
            )
        )
    return result


async def upsert_shelf(
    db: AsyncSession, user: User, item_id: int, payload: ShelfUpsert
) -> ShelfEntryRead:
    item = await get_visible_item(db, item_id, user)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Карточка не найдена")

    entry = await db.scalar(
        select(ShelfEntry)
        .where(ShelfEntry.user_id == user.id, ShelfEntry.item_id == item_id)
        .options(selectinload(ShelfEntry.item))
    )

    if entry:
        entry.status = payload.status
        entry.finished_at = payload.finished_at
    else:
        entry = ShelfEntry(
            user_id=user.id,
            item_id=item_id,
            status=payload.status,
            finished_at=payload.finished_at,
        )
        db.add(entry)

    await db.commit()
    await db.refresh(entry)

    # Загружаем item и user_rating
    user_rating = await db.scalar(
        select(Rating.value).where(Rating.user_id == user.id, Rating.item_id == item_id)
    )

    return ShelfEntryRead(
        id=entry.id,
        item_id=entry.item_id,
        status=entry.status,
        finished_at=entry.finished_at,
        item=item,
        user_rating=user_rating,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


async def delete_shelf(db: AsyncSession, user: User, item_id: int) -> None:
    entry = await db.scalar(
        select(ShelfEntry).where(ShelfEntry.user_id == user.id, ShelfEntry.item_id == item_id)
    )
    if not entry:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Запись на полке не найдена")
    await db.delete(entry)
    await db.commit()


async def set_rating(
    db: AsyncSession, user: User, item_id: int, value: int
) -> RatingResult:
    item = await get_visible_item(db, item_id, user)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Карточка не найдена")

    rating = await db.scalar(
        select(Rating).where(Rating.user_id == user.id, Rating.item_id == item_id)
    )
    if rating:
        rating.value = value
    else:
        rating = Rating(user_id=user.id, item_id=item_id, value=value)
        db.add(rating)

    await db.commit()
    await recompute_item_rating(db, item_id)
    await db.refresh(item)

    return RatingResult(
        value=value,
        rating_avg=float(item.rating_avg),
        ratings_count=item.ratings_count,
    )


async def delete_rating(db: AsyncSession, user: User, item_id: int) -> None:
    rating = await db.scalar(
        select(Rating).where(Rating.user_id == user.id, Rating.item_id == item_id)
    )
    if not rating:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Оценка не найдена")

    await db.delete(rating)
    await db.commit()
    await recompute_item_rating(db, item_id)


async def recompute_item_rating(db: AsyncSession, item_id: int) -> None:
    stmt = select(
        func.avg(Rating.value),
        func.count(Rating.id),
    ).where(Rating.item_id == item_id)
    avg_val, count_val = (await db.execute(stmt)).one()

    item = await db.scalar(select(CatalogItem).where(CatalogItem.id == item_id))
    if item:
        item.rating_avg = Decimal(str(round(float(avg_val or 0.0), 2)))
        item.ratings_count = int(count_val or 0)
        await db.commit()
        await db.refresh(item)
