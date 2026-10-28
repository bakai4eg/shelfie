"""Полки и оценки текущего пользователя (ТЗ 4.2.2, 4.4.1, 4.4.2)."""

from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.library import (
    RatingResult,
    RatingUpsert,
    ShelfEntryRead,
    ShelfStatus,
    ShelfUpsert,
)
from app.services.library import (
    delete_rating,
    delete_shelf,
    list_shelf,
    set_rating,
    upsert_shelf,
)

router = APIRouter(prefix="/me", tags=["library"])


@router.get("/library", response_model=list[ShelfEntryRead], summary="Моя библиотека / полки")
async def get_my_library(
    db: SessionDep,
    user: CurrentUser,
    status: ShelfStatus | None = None,
    type: str | None = None,
    sort: Annotated[
        str, Query(pattern="^(added_desc|rating_desc|title_asc)$")
    ] = "added_desc",
) -> list[ShelfEntryRead]:
    return await list_shelf(db, user, status_filter=status, item_type=type, sort=sort)


@router.put(
    "/library/{item_id}",
    response_model=ShelfEntryRead,
    summary="Добавить / обновить полку",
)
async def update_my_shelf(
    item_id: int,
    payload: ShelfUpsert,
    db: SessionDep,
    user: CurrentUser,
) -> ShelfEntryRead:
    return await upsert_shelf(db, user, item_id, payload)


@router.delete(
    "/library/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить карточку с полки",
)
async def remove_from_shelf(
    item_id: int,
    db: SessionDep,
    user: CurrentUser,
) -> Response:
    await delete_shelf(db, user, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/ratings/{item_id}", response_model=RatingResult, summary="Поставить оценку")
async def update_my_rating(
    item_id: int,
    payload: RatingUpsert,
    db: SessionDep,
    user: CurrentUser,
) -> RatingResult:
    return await set_rating(db, user, item_id, payload.value)


@router.delete(
    "/ratings/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить оценку",
)
async def remove_my_rating(
    item_id: int,
    db: SessionDep,
    user: CurrentUser,
) -> Response:
    await delete_rating(db, user, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
