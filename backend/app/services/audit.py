"""Запись в журнал действий (ТЗ 4.6.3, 4.6.5)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.user import User

# Действия журнала. Строки фиксированы: по ним фильтруется панель администратора.
REPORT_RESOLVE = "report.resolve"
CONTENT_HIDE = "content.hide"
CONTENT_DELETE = "content.delete"
CARD_APPROVE = "card.approve"
CARD_REJECT = "card.reject"
USER_ROLE = "user.role"
USER_BLOCK = "user.block"
USER_UNBLOCK = "user.unblock"
USER_DELETE = "user.delete"

AUDIT_ACTIONS = (
    REPORT_RESOLVE,
    CONTENT_HIDE,
    CONTENT_DELETE,
    CARD_APPROVE,
    CARD_REJECT,
    USER_ROLE,
    USER_BLOCK,
    USER_UNBLOCK,
    USER_DELETE,
)


def record(
    db: AsyncSession,
    actor: User,
    action: str,
    target_type: str | None = None,
    target_id: int | None = None,
    **details: object,
) -> None:
    """Добавляет запись в ту же транзакцию, что и само действие: коммитит вызывающий."""
    db.add(
        AuditLog(
            actor_id=actor.id,
            actor_login=actor.login,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
        )
    )
