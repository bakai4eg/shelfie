"""Поиск и фильтры каталога (T2.1, ТЗ 4.3.1).

Видимость карточек — единственное место, где решается, что попадёт в выдачу:
`approved` видят все, `pending` — только автор (и модераторы с админом),
`hidden` — никто. Фильтры панели строятся по тому же правилу, иначе в
панели появлялись бы жанры скрытых карточек.
"""

from fastapi import HTTPException, status
from sqlalchemy import String, and_, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import (
    MODERATION_APPROVED,
    MODERATION_HIDDEN,
    MODERATION_PENDING,
    ROLE_ADMIN,
    ROLE_MODERATOR,
    SOURCE_LOCAL,
)
from app.core.media import delete_poster, save_poster
from app.models.catalog import CatalogItem
from app.models.user import User

_SORT_COLUMNS = {
    "year_desc": (CatalogItem.year.desc().nullslast(), CatalogItem.id.desc()),
    "rating_desc": (CatalogItem.rating_avg.desc(), CatalogItem.ratings_count.desc()),
    "title_asc": (CatalogItem.title_normalized.asc(), CatalogItem.id.asc()),
}


def visibility_clause(user: User | None):
    """Условие выборки, общее для поиска и панели фильтров."""
    if user is None:
        return CatalogItem.moderation_status == MODERATION_APPROVED
    if user.role in (ROLE_MODERATOR, ROLE_ADMIN):
        return CatalogItem.moderation_status != MODERATION_HIDDEN
    return or_(
        CatalogItem.moderation_status == MODERATION_APPROVED,
        and_(
            CatalogItem.moderation_status == MODERATION_PENDING,
            CatalogItem.created_by == user.id,
        ),
    )


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _search_pattern(query: str) -> str:
    return f"%{_escape_like(query.strip().lower())}%"


def _relevance_order(query: str):
    """Точное совпадение → начинается с запроса → совпало где-то внутри."""
    needle = query.strip().lower()
    prefix = f"{_escape_like(needle)}%"
    return (
        case(
            (CatalogItem.title_normalized == needle, 0),
            (CatalogItem.title_normalized.like(prefix, escape="\\"), 1),
            else_=2,
        ),
        CatalogItem.year.desc().nullslast(),
        CatalogItem.id.desc(),
    )


async def search_catalog(
    db: AsyncSession,
    *,
    user: User | None,
    query: str | None = None,
    item_type: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    genre: str | None = None,
    country: str | None = None,
    source: str | None = None,
    local_only: bool = False,
    sort: str = "relevance",
    page: int = 1,
    size: int = 20,
    sync_external: bool = True,
) -> tuple[list[CatalogItem], int]:
    """Возвращает страницу карточек и общее количество по фильтрам."""
    if (
        sync_external
        and settings.enable_external_providers
        and query
        and query.strip()
        and not local_only
        and source != SOURCE_LOCAL
    ):
        from app.services.integrations import sync_external_catalog

        try:
            await sync_external_catalog(db, query, item_type)
        except Exception:
            pass  # сбои внешних сетей не прерывают локальный поиск

    conditions = [visibility_clause(user)]

    if query and query.strip():
        pattern = _search_pattern(query)
        conditions.append(CatalogItem.title_normalized.like(pattern, escape="\\"))
    if item_type:
        conditions.append(CatalogItem.type == item_type)
    if year_from is not None:
        conditions.append(CatalogItem.year >= year_from)
    if year_to is not None:
        conditions.append(CatalogItem.year <= year_to)
    if genre:
        # JSON-список сериализуется с кавычками: точное совпадение элемента.
        conditions.append(cast(CatalogItem.genres, String).like(f'%"{genre}"%'))
    if country:
        conditions.append(CatalogItem.country == country)
    if source:
        conditions.append(CatalogItem.source == source)
    if local_only:
        conditions.append(CatalogItem.is_local.is_(True))

    base = select(CatalogItem).where(*conditions)
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0

    if sort == "relevance" and query and query.strip():
        order_by = _relevance_order(query)
    elif sort in _SORT_COLUMNS:
        order_by = _SORT_COLUMNS[sort]
    else:
        # relevance без запроса: сначала то, что выше оценили.
        order_by = (
            CatalogItem.rating_avg.desc(),
            CatalogItem.ratings_count.desc(),
            CatalogItem.id.desc(),
        )

    stmt = base.order_by(*order_by).offset((page - 1) * size).limit(size)
    items = list((await db.scalars(stmt)).all())
    return items, total


async def catalog_filters(db: AsyncSession, *, user: User | None) -> dict:
    """Значения панели фильтров по видимым карточкам."""
    visible = visibility_clause(user)

    types = list((await db.scalars(select(CatalogItem.type).where(visible).distinct())).all())
    sources = list((await db.scalars(select(CatalogItem.source).where(visible).distinct())).all())
    countries = list(
        (
            await db.scalars(
                select(CatalogItem.country)
                .where(visible, CatalogItem.country.is_not(None))
                .distinct()
            )
        ).all()
    )
    year_min, year_max = (
        await db.execute(
            select(func.min(CatalogItem.year), func.max(CatalogItem.year)).where(visible)
        )
    ).one()

    genre_rows = (await db.scalars(select(CatalogItem.genres).where(visible))).all()
    genres = sorted({genre for row in genre_rows for genre in (row or [])}, key=str.casefold)

    return {
        "types": sorted(types),
        "sources": sorted(sources),
        "genres": genres,
        "countries": sorted(countries, key=str.casefold),
        "year_min": year_min,
        "year_max": year_max,
    }


async def create_local_card(
    db: AsyncSession,
    user: User,
    *,
    item_type: str,
    title: str,
    original_title: str | None = None,
    year: int | None = None,
    country: str | None = None,
    genres: list[str] | None = None,
    description: str | None = None,
    is_local: bool = True,
    poster: tuple[bytes, str] | None = None,
) -> CatalogItem:
    """Создаёт карточку сообщества (ТЗ 4.3.3).

    Всегда `source = local`, `moderation_status = pending`: карточка видна
    автору и модераторам, а в публичный каталог попадёт после проверки (T4.2).
    """
    poster_path = save_poster(*poster) if poster else None
    item = CatalogItem(
        type=item_type,
        source=SOURCE_LOCAL,
        title=title,
        original_title=original_title,
        year=year,
        country=country,
        genres=list(genres or []),
        description=description,
        poster_path=poster_path,
        is_local=is_local,
        moderation_status=MODERATION_PENDING,
        created_by=user.id,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def update_local_card(
    db: AsyncSession,
    user: User,
    item_id: int,
    *,
    payload: dict[str, object],
    poster: tuple[bytes, str] | None = None,
    remove_poster: bool = False,
) -> CatalogItem:
    """Правка своей карточки, пока она на проверке (T2.3)."""
    item = await db.scalar(
        select(CatalogItem).where(
            CatalogItem.id == item_id,
            CatalogItem.source == SOURCE_LOCAL,
            CatalogItem.created_by == user.id,
        )
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Карточка не найдена")
    if item.moderation_status != MODERATION_PENDING:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Карточка уже проверена — изменения недоступны",
        )

    for field in (
        "type",
        "title",
        "original_title",
        "year",
        "country",
        "genres",
        "description",
        "is_local",
    ):
        if field in payload:
            setattr(item, field, payload[field])

    old_poster = item.poster_path
    if poster:
        item.poster_path = save_poster(*poster)
    elif remove_poster:
        item.poster_path = None

    await db.commit()
    await db.refresh(item)

    # Старый файл удаляем только после успешного коммита, чтобы не потерять
    # обложку при ошибке записи в БД.
    if old_poster and old_poster != item.poster_path:
        delete_poster(old_poster)
    return item


async def list_my_local_cards(
    db: AsyncSession,
    user: User,
    *,
    page: int = 1,
    size: int = 20,
) -> tuple[list[CatalogItem], int]:
    """Все локальные карточки автора, включая ожидающие проверки."""
    conditions = (
        CatalogItem.created_by == user.id,
        CatalogItem.source == SOURCE_LOCAL,
    )
    total = (await db.scalar(select(func.count()).select_from(CatalogItem).where(*conditions))) or 0
    stmt = (
        select(CatalogItem)
        .where(*conditions)
        .order_by(CatalogItem.created_at.desc(), CatalogItem.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return list((await db.scalars(stmt)).all()), total


async def find_local_duplicates(
    db: AsyncSession,
    user: User,
    *,
    title: str,
    year: int | None = None,
    limit: int = 10,
) -> list[CatalogItem]:
    """Похожие карточки до сохранения: совпадение по названию, год — приоритет."""
    needle = title.strip()
    pattern = _search_pattern(needle)
    conditions = [
        visibility_clause(user),
        CatalogItem.title_normalized.like(pattern, escape="\\"),
    ]

    order = [case((CatalogItem.title_normalized == needle.lower(), 0), else_=1)]
    if year is not None:
        order.append(case((CatalogItem.year == year, 0), else_=1))
    order.extend([CatalogItem.year.desc().nullslast(), CatalogItem.id.desc()])

    stmt = select(CatalogItem).where(*conditions).order_by(*order).limit(limit)
    return list((await db.scalars(stmt)).all())
