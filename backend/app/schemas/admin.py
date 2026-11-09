"""Схемы администрирования (ТЗ 4.6.4, 4.6.5). Контракт — docs/api.md, раздел 11."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class AdminUserRead(BaseModel):
    id: int
    login: str
    email: str
    role: str
    is_blocked: bool
    avatar_url: str | None = None
    created_at: datetime


class RoleChange(BaseModel):
    # Администратора через интерфейс не назначают: первый админ создаётся скриптом set_role.
    role: Literal["user", "moderator"]


class AdminSummary(BaseModel):
    users: int
    cards: int
    reviews: int
    open_reports: int


class AuditRead(BaseModel):
    id: int
    actor_id: int | None = None
    actor_login: str
    action: str
    target_type: str | None = None
    target_id: int | None = None
    details: dict
    created_at: datetime
