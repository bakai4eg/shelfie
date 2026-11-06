"""Сервис списков-витрин (ТЗ 4.4.3)."""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.media import avatar_url
from app.models.catalog import CatalogItem
from app.models.lists import ListItem, UserList
from app.models.user import User
from app.schemas.catalog import CatalogItemRead
from app.schemas.lists import (
    ListCreate,
    ListDetail,
    ListItemAdd,
    ListItemRead,
    ListItemUpdate,
    ListOwner,
    ListSummary,
    ListUpdate,
)
from app.services.catalog import visibility_clause


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Список не найден")


async def _items_count(db: AsyncSession, list_id: int, viewer: User | None) -> int:
    return (
        await db.scalar(
            select(func.count())
            .select_from(ListItem)
            .join(CatalogItem, CatalogItem.id == ListItem.item_id)
            .where(ListItem.list_id == list_id, visibility_clause(viewer))
        )
        or 0
    )


async def _summary(db: AsyncSession, lst: UserList, viewer: User | None) -> ListSummary:
    summary = ListSummary.model_validate(lst)
    summary.items_count = await _items_count(db, lst.id, viewer)
    return summary


async def _detail(db: AsyncSession, lst: UserList, viewer: User | None) -> ListDetail:
    """Скрытые модератором карточки в список не попадают ни у владельца, ни в витрине."""
    rows = (
        await db.execute(
            select(ListItem, CatalogItem)
            .join(CatalogItem, CatalogItem.id == ListItem.item_id)
            .where(ListItem.list_id == lst.id, visibility_clause(viewer))
            .order_by(ListItem.position, ListItem.id)
        )
    ).all()
    owner = await db.get(User, lst.user_id)
    base = ListSummary.model_validate(lst).model_dump(exclude={"items_count"})
    return ListDetail(
        **base,
        items_count=len(rows),
        owner=ListOwner(login=owner.login, avatar_url=avatar_url(owner.avatar_path)),
        items=[
            ListItemRead(
                position=index,
                note=entry.note,
                item=CatalogItemRead.model_validate(item),
            )
            for index, (entry, item) in enumerate(rows)
        ],
    )


async def _own_list(db: AsyncSession, user: User, list_id: int) -> UserList:
    lst = await db.get(UserList, list_id)
    # чужой список выглядит как несуществующий: не раскрываем, что он есть
    if lst is None or lst.user_id != user.id:
        raise _not_found()
    return lst


async def _own_entry(db: AsyncSession, lst: UserList, item_id: int) -> ListItem:
    entry = await db.scalar(
        select(ListItem).where(ListItem.list_id == lst.id, ListItem.item_id == item_id)
    )
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Карточки нет в списке")
    return entry


async def my_lists(db: AsyncSession, user: User) -> list[ListSummary]:
    rows = (
        await db.scalars(
            select(UserList)
            .where(UserList.user_id == user.id)
            .order_by(UserList.updated_at.desc(), UserList.id.desc())
        )
    ).all()
    return [await _summary(db, lst, user) for lst in rows]


async def create_list(db: AsyncSession, user: User, payload: ListCreate) -> ListDetail:
    lst = UserList(user_id=user.id, **payload.model_dump())
    db.add(lst)
    await db.commit()
    await db.refresh(lst)
    return await _detail(db, lst, user)


async def get_my_list(db: AsyncSession, user: User, list_id: int) -> ListDetail:
    return await _detail(db, await _own_list(db, user, list_id), user)


async def update_list(
    db: AsyncSession, user: User, list_id: int, payload: ListUpdate
) -> ListDetail:
    lst = await _own_list(db, user, list_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if key in ("title", "is_public", "theme") and value is None:
            continue
        setattr(lst, key, value)
    await db.commit()
    await db.refresh(lst)
    return await _detail(db, lst, user)


async def delete_list(db: AsyncSession, user: User, list_id: int) -> None:
    lst = await _own_list(db, user, list_id)
    await db.delete(lst)
    await db.commit()


async def _touch(db: AsyncSession, lst: UserList, user: User) -> ListDetail:
    lst.updated_at = func.now()
    await db.commit()
    await db.refresh(lst)
    return await _detail(db, lst, user)


async def add_item(db: AsyncSession, user: User, list_id: int, payload: ListItemAdd) -> ListDetail:
    lst = await _own_list(db, user, list_id)
    item = await db.scalar(
        select(CatalogItem).where(CatalogItem.id == payload.item_id, visibility_clause(user))
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Карточка не найдена")
    exists = await db.scalar(
        select(ListItem.id).where(ListItem.list_id == lst.id, ListItem.item_id == item.id)
    )
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Карточка уже есть в списке"
        )
    last = await db.scalar(select(func.max(ListItem.position)).where(ListItem.list_id == lst.id))
    db.add(
        ListItem(
            list_id=lst.id,
            item_id=item.id,
            position=0 if last is None else last + 1,
            note=payload.note,
        )
    )
    return await _touch(db, lst, user)


async def update_note(
    db: AsyncSession, user: User, list_id: int, item_id: int, payload: ListItemUpdate
) -> ListDetail:
    lst = await _own_list(db, user, list_id)
    entry = await _own_entry(db, lst, item_id)
    entry.note = payload.note
    return await _touch(db, lst, user)


async def remove_item(db: AsyncSession, user: User, list_id: int, item_id: int) -> ListDetail:
    lst = await _own_list(db, user, list_id)
    entry = await _own_entry(db, lst, item_id)
    await db.delete(entry)
    await db.flush()
    entries = (
        await db.scalars(
            select(ListItem)
            .where(ListItem.list_id == lst.id)
            .order_by(ListItem.position, ListItem.id)
        )
    ).all()
    for index, rest in enumerate(entries):
        rest.position = index
    return await _touch(db, lst, user)


async def reorder(db: AsyncSession, user: User, list_id: int, item_ids: list[int]) -> ListDetail:
    lst = await _own_list(db, user, list_id)
    entries = (await db.scalars(select(ListItem).where(ListItem.list_id == lst.id))).all()
    by_item = {entry.item_id: entry for entry in entries}
    if len(item_ids) != len(set(item_ids)) or set(item_ids) != set(by_item):
        raise HTTPException(
            status_code=422,
            detail="Порядок должен содержать ровно все карточки списка без повторов",
        )
    for index, item_id in enumerate(item_ids):
        by_item[item_id].position = index
    return await _touch(db, lst, user)


async def public_list(db: AsyncSession, list_id: int) -> ListDetail:
    lst = await db.get(UserList, list_id)
    if lst is None or not lst.is_public:
        raise _not_found()
    owner = await db.get(User, lst.user_id)
    if owner is None or owner.is_blocked:
        raise _not_found()
    return await _detail(db, lst, None)


async def public_lists_of(
    db: AsyncSession, owner: User, page: int, size: int
) -> tuple[list[ListSummary], int]:
    condition = (UserList.user_id == owner.id) & UserList.is_public.is_(True)
    total = await db.scalar(select(func.count()).select_from(UserList).where(condition)) or 0
    rows = (
        await db.scalars(
            select(UserList)
            .where(condition)
            .order_by(UserList.updated_at.desc(), UserList.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    ).all()
    return [await _summary(db, lst, None) for lst in rows], total
