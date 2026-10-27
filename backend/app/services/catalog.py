"""Поиск и фильтры каталога (T2.1, ТЗ 4.3.1).

Видимость карточек — единственное место, где решается, что попадёт в выдачу:
`approved` видят все, `pending` — только автор (и модераторы с админом),
`hidden` — никто. Фильтры панели строятся по тому же правилу, иначе в
панели появлялись бы жанры скрытых карточек.
"""

from sqlalchemy import String, and_, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    MODERATION_APPROVED,
    MODERATION_HIDDEN,
    MODERATION_PENDING,
    ROLE_ADMIN,
    ROLE_MODERATOR,
)
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
) -> tuple[list[CatalogItem], int]:
    """Возвращает страницу карточек и общее количество по фильтрам."""
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

    stmt = (
        base.order_by(*order_by)
        .offset((page - 1) * size)
        .limit(size)
    )
    items = list((await db.scalars(stmt)).all())
    return items, total


async def catalog_filters(db: AsyncSession, *, user: User | None) -> dict:
    """Значения панели фильтров по видимым карточкам."""
    visible = visibility_clause(user)

    types = list(
        (await db.scalars(select(CatalogItem.type).where(visible).distinct())).all()
    )
    sources = list(
        (await db.scalars(select(CatalogItem.source).where(visible).distinct())).all()
    )
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

    genre_rows = (
        await db.scalars(select(CatalogItem.genres).where(visible))
    ).all()
    genres = sorted({genre for row in genre_rows for genre in (row or [])}, key=str.casefold)

    return {
        "types": sorted(types),
        "sources": sorted(sources),
        "genres": genres,
        "countries": sorted(countries, key=str.casefold),
        "year_min": year_min,
        "year_max": year_max,
    }
