"""Списки-витрины (ТЗ 4.4.3). Контракт: docs/api.md, раздел 6."""

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.lists import (
    ListCreate,
    ListDetail,
    ListItemAdd,
    ListItemUpdate,
    ListOrder,
    ListSummary,
    ListUpdate,
)
from app.services import lists as service

router = APIRouter(tags=["lists"])


@router.get("/me/lists", response_model=list[ListSummary], summary="Мои списки")
async def get_my_lists(db: SessionDep, user: CurrentUser) -> list[ListSummary]:
    return await service.my_lists(db, user)


@router.post(
    "/me/lists",
    response_model=ListDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Создать список",
)
async def post_list(payload: ListCreate, db: SessionDep, user: CurrentUser) -> ListDetail:
    return await service.create_list(db, user, payload)


@router.get("/me/lists/{list_id}", response_model=ListDetail, summary="Мой список")
async def get_list(list_id: int, db: SessionDep, user: CurrentUser) -> ListDetail:
    return await service.get_my_list(db, user, list_id)


@router.patch("/me/lists/{list_id}", response_model=ListDetail, summary="Изменить список")
async def patch_list(
    list_id: int, payload: ListUpdate, db: SessionDep, user: CurrentUser
) -> ListDetail:
    return await service.update_list(db, user, list_id, payload)


@router.delete(
    "/me/lists/{list_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить список"
)
async def remove_list(list_id: int, db: SessionDep, user: CurrentUser) -> Response:
    await service.delete_list(db, user, list_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/me/lists/{list_id}/items",
    response_model=ListDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить карточку в список",
)
async def post_list_item(
    list_id: int, payload: ListItemAdd, db: SessionDep, user: CurrentUser
) -> ListDetail:
    return await service.add_item(db, user, list_id, payload)


@router.put(
    "/me/lists/{list_id}/order",
    response_model=ListDetail,
    summary="Сохранить порядок карточек",
)
async def put_list_order(
    list_id: int, payload: ListOrder, db: SessionDep, user: CurrentUser
) -> ListDetail:
    return await service.reorder(db, user, list_id, payload.item_ids)


@router.patch(
    "/me/lists/{list_id}/items/{item_id}",
    response_model=ListDetail,
    summary="Изменить заметку",
)
async def patch_list_item(
    list_id: int, item_id: int, payload: ListItemUpdate, db: SessionDep, user: CurrentUser
) -> ListDetail:
    return await service.update_note(db, user, list_id, item_id, payload)


@router.delete(
    "/me/lists/{list_id}/items/{item_id}",
    response_model=ListDetail,
    summary="Убрать карточку из списка",
)
async def delete_list_item(
    list_id: int, item_id: int, db: SessionDep, user: CurrentUser
) -> ListDetail:
    return await service.remove_item(db, user, list_id, item_id)


@router.get(
    "/public/lists/{list_id}",
    response_model=ListDetail,
    summary="Публичная витрина списка",
)
async def get_public_list(list_id: int, db: SessionDep) -> ListDetail:
    return await service.public_list(db, list_id)
