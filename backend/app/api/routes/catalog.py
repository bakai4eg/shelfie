"""Каталог: поиск и фильтры (T2.1). Карточка и внешние источники — T2.2/T3.4."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import OptionalUser, SessionDep
from app.schemas.catalog import (
    CatalogFilters,
    CatalogItemRead,
    CatalogSort,
    CatalogSource,
    CatalogType,
)
from app.schemas.common import Page
from app.services.catalog import catalog_filters, search_catalog

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("", response_model=Page[CatalogItemRead], summary="Поиск по каталогу")
async def list_catalog(
    db: SessionDep,
    user: OptionalUser,
    q: Annotated[
        str | None,
        Query(max_length=200, description="Название или оригинальное название"),
    ] = None,
    type: CatalogType | None = None,
    year_from: Annotated[int | None, Query(ge=0, le=3000)] = None,
    year_to: Annotated[int | None, Query(ge=0, le=3000)] = None,
    genre: Annotated[str | None, Query(max_length=100)] = None,
    country: Annotated[str | None, Query(max_length=100)] = None,
    source: CatalogSource | None = None,
    local_only: bool = False,
    sort: CatalogSort = "relevance",
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[CatalogItemRead]:
    if year_from is not None and year_to is not None and year_from > year_to:
        year_from, year_to = year_to, year_from

    items, total = await search_catalog(
        db,
        user=user,
        query=q,
        item_type=type,
        year_from=year_from,
        year_to=year_to,
        genre=genre,
        country=country,
        source=source,
        local_only=local_only,
        sort=sort,
        page=page,
        size=size,
    )
    return Page[CatalogItemRead](
        items=[CatalogItemRead.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/filters", response_model=CatalogFilters, summary="Значения фильтров")
async def get_filters(db: SessionDep, user: OptionalUser) -> CatalogFilters:
    return CatalogFilters(**await catalog_filters(db, user=user))
