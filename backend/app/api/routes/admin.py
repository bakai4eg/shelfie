"""Администрирование: пользователи, сводка, журнал (ТЗ 4.6.4, 4.6.5)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import SessionDep, require_admin
from app.models.user import User
from app.schemas.admin import AdminSummary, AdminUserRead, AuditRead, RoleChange
from app.schemas.common import Page
from app.services import admin as service

router = APIRouter(prefix="/admin", tags=["admin"])

AdminUser = Annotated[User, Depends(require_admin)]


@router.get("/summary", response_model=AdminSummary, summary="Сводка по системе")
async def get_summary(db: SessionDep, _admin: AdminUser) -> AdminSummary:
    return await service.summary(db)


@router.get("/users", response_model=Page[AdminUserRead], summary="Пользователи")
async def get_users(
    db: SessionDep,
    _admin: AdminUser,
    q: str | None = None,
    role: Annotated[str | None, Query(pattern="^(user|moderator|admin)$")] = None,
    is_blocked: bool | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[AdminUserRead]:
    return await service.list_users(db, q=q, role=role, is_blocked=is_blocked, page=page, size=size)


@router.patch(
    "/users/{user_id}/role", response_model=AdminUserRead, summary="Назначить или снять модератора"
)
async def patch_role(
    user_id: int, payload: RoleChange, db: SessionDep, admin: AdminUser
) -> AdminUserRead:
    return await service.change_role(db, admin, user_id, payload.role)


@router.post("/users/{user_id}/block", response_model=AdminUserRead, summary="Заблокировать")
async def post_block(user_id: int, db: SessionDep, admin: AdminUser) -> AdminUserRead:
    return await service.block_user(db, admin, user_id)


@router.post("/users/{user_id}/unblock", response_model=AdminUserRead, summary="Разблокировать")
async def post_unblock(user_id: int, db: SessionDep, admin: AdminUser) -> AdminUserRead:
    return await service.unblock_user(db, admin, user_id)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить пользователя со всеми данными",
)
async def remove_user(user_id: int, db: SessionDep, admin: AdminUser) -> Response:
    await service.remove_user(db, admin, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/audit", response_model=Page[AuditRead], summary="Журнал действий")
async def get_audit(
    db: SessionDep,
    _admin: AdminUser,
    action: str | None = None,
    actor: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[AuditRead]:
    return await service.list_audit(
        db,
        action=action,
        actor=actor,
        date_from=date_from,
        date_to=date_to,
        page=page,
        size=size,
    )
