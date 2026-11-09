"""Сервис администрирования (ТЗ 4.6.4, 4.6.5)."""

from datetime import UTC, date, datetime, time, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ROLE_ADMIN
from app.core.media import avatar_url, delete_image
from app.models.audit import AuditLog
from app.models.catalog import CatalogItem
from app.models.moderation import Report
from app.models.social import Review
from app.models.user import User
from app.schemas.admin import AdminSummary, AdminUserRead, AuditRead
from app.schemas.common import Page
from app.services import audit
from app.services.auth import revoke_all_sessions
from app.services.cleanup import delete_user as cascade_delete_user
from app.services.moderation import REPORT_OPEN


def _read(user: User) -> AdminUserRead:
    return AdminUserRead(
        id=user.id,
        login=user.login,
        email=user.email,
        role=user.role,
        is_blocked=user.is_blocked,
        avatar_url=avatar_url(user.avatar_path),
        created_at=user.created_at,
    )


async def _target(db: AsyncSession, admin: User, user_id: int) -> User:
    """Над собой и над другими администраторами действий нет: иначе можно остаться без админа."""
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
    if user.id == admin.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Нельзя менять собственную учётную запись")
    if user.role == ROLE_ADMIN:
        raise HTTPException(status.HTTP_409_CONFLICT, "Нельзя менять учётную запись администратора")
    return user


async def list_users(
    db: AsyncSession,
    *,
    q: str | None,
    role: str | None,
    is_blocked: bool | None,
    page: int,
    size: int,
) -> Page[AdminUserRead]:
    condition = []
    if q and q.strip():
        needle = f"%{q.strip().lower()}%"
        condition.append(
            or_(func.lower(User.login).like(needle), func.lower(User.email).like(needle))
        )
    if role:
        condition.append(User.role == role)
    if is_blocked is not None:
        condition.append(User.is_blocked.is_(is_blocked))

    total = await db.scalar(select(func.count()).select_from(User).where(*condition)) or 0
    rows = (
        await db.scalars(
            select(User)
            .where(*condition)
            .order_by(User.created_at.desc(), User.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    ).all()
    return Page[AdminUserRead](items=[_read(u) for u in rows], total=total, page=page, size=size)


async def change_role(db: AsyncSession, admin: User, user_id: int, role: str) -> AdminUserRead:
    user = await _target(db, admin, user_id)
    old, user.role = user.role, role
    audit.record(
        db, admin, audit.USER_ROLE, "user", user.id, login=user.login, before=old, after=role
    )
    await db.commit()
    return _read(user)


async def block_user(db: AsyncSession, admin: User, user_id: int) -> AdminUserRead:
    user = await _target(db, admin, user_id)
    user.is_blocked = True
    audit.record(db, admin, audit.USER_BLOCK, "user", user.id, login=user.login)
    await db.commit()
    # Закрываем все устройства: заблокированный не должен продолжать работать с живым токеном.
    await revoke_all_sessions(db, user.id)
    return _read(user)


async def unblock_user(db: AsyncSession, admin: User, user_id: int) -> AdminUserRead:
    user = await _target(db, admin, user_id)
    user.is_blocked = False
    audit.record(db, admin, audit.USER_UNBLOCK, "user", user.id, login=user.login)
    await db.commit()
    return _read(user)


async def remove_user(db: AsyncSession, admin: User, user_id: int) -> None:
    user = await _target(db, admin, user_id)
    login = user.login
    audit.record(db, admin, audit.USER_DELETE, "user", user.id, login=login)
    files = await cascade_delete_user(db, user)
    await db.commit()
    for path in files:
        delete_image(path)


async def summary(db: AsyncSession) -> AdminSummary:
    """Четыре SQL-агрегата, без выгрузки строк в память."""
    users = await db.scalar(select(func.count()).select_from(User))
    cards = await db.scalar(select(func.count()).select_from(CatalogItem))
    reviews = await db.scalar(select(func.count()).select_from(Review))
    open_reports = await db.scalar(
        select(func.count()).select_from(Report).where(Report.status == REPORT_OPEN)
    )
    return AdminSummary(
        users=users or 0, cards=cards or 0, reviews=reviews or 0, open_reports=open_reports or 0
    )


async def list_audit(
    db: AsyncSession,
    *,
    action: str | None,
    actor: str | None,
    date_from: date | None,
    date_to: date | None,
    page: int,
    size: int,
) -> Page[AuditRead]:
    condition = []
    if action:
        condition.append(AuditLog.action == action)
    if actor and actor.strip():
        condition.append(func.lower(AuditLog.actor_login).like(f"%{actor.strip().lower()}%"))
    if date_from:
        condition.append(AuditLog.created_at >= datetime.combine(date_from, time.min, tzinfo=UTC))
    if date_to:
        condition.append(
            AuditLog.created_at
            < datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=UTC)
        )

    total = await db.scalar(select(func.count()).select_from(AuditLog).where(*condition)) or 0
    rows = (
        await db.scalars(
            select(AuditLog)
            .where(*condition)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    ).all()
    items = [
        AuditRead(
            id=r.id,
            actor_id=r.actor_id,
            actor_login=r.actor_login,
            action=r.action,
            target_type=r.target_type,
            target_id=r.target_id,
            details=r.details or {},
            created_at=r.created_at,
        )
        for r in rows
    ]
    return Page[AuditRead](items=items, total=total, page=page, size=size)
