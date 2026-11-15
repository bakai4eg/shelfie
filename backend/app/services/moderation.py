"""Сервис жалоб и модерации (ТЗ 4.6.2, 4.6.3)."""

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    MODERATION_APPROVED,
    MODERATION_HIDDEN,
    MODERATION_PENDING,
    SOURCE_LOCAL,
)
from app.core.media import delete_image
from app.models.catalog import CatalogItem
from app.models.moderation import Report
from app.models.social import Comment, Review
from app.models.user import User
from app.schemas.catalog import CatalogItemRead
from app.schemas.moderation import (
    ModerationCardRead,
    ReportCreate,
    ReportRead,
)
from app.services import audit
from app.services.cleanup import delete_card, delete_comments, delete_reviews

REPORT_OPEN = "open"
REPORT_RESOLVED = "resolved"
REPORT_CLOSED = "closed"


# --- Жалобы пользователей (T4.1) ---


async def _target_context(
    db: AsyncSession, target_type: str, target_id: int
) -> tuple[str | None, str | None]:
    """Название и автор объекта жалобы: модератору нужен контекст, а не голый id."""
    if target_type == "review":
        row = (
            await db.execute(
                select(Review.title, User.login)
                .join(User, User.id == Review.user_id)
                .where(Review.id == target_id)
            )
        ).first()
        return (row[0], row[1]) if row else (None, None)
    if target_type == "comment":
        row = (
            await db.execute(
                select(Comment.body, User.login)
                .join(User, User.id == Comment.user_id)
                .where(Comment.id == target_id)
            )
        ).first()
        return (row[0][:80], row[1]) if row else (None, None)
    if target_type == "card":
        row = (
            await db.execute(
                select(CatalogItem.title, User.login)
                .outerjoin(User, User.id == CatalogItem.created_by)
                .where(CatalogItem.id == target_id)
            )
        ).first()
        return (row[0], row[1]) if row else (None, None)
    if target_type == "profile":
        login = await db.scalar(select(User.login).where(User.id == target_id))
        return (f"Профиль @{login}", login) if login else (None, None)
    return None, None


async def _to_read(db: AsyncSession, report: Report, reporter_login: str) -> ReportRead:
    title, author = await _target_context(db, report.target_type, report.target_id)
    return ReportRead(
        id=report.id,
        reporter_id=report.reporter_id,
        reporter_login=reporter_login,
        target_type=report.target_type,
        target_id=report.target_id,
        target_title=title,
        target_author=author,
        reason=report.reason,
        comment=report.comment,
        status=report.status,
        resolution=report.resolution,
        resolution_reason=report.resolution_reason,
        resolved_by=report.resolved_by,
        resolved_at=report.resolved_at,
        created_at=report.created_at,
    )


async def create_report(db: AsyncSession, user: User, payload: ReportCreate) -> ReportRead:
    title, author = await _target_context(db, payload.target_type, payload.target_id)
    if title is None:
        names = {
            "review": "Рецензия",
            "comment": "Комментарий",
            "card": "Карточка",
            "profile": "Профиль",
        }
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{names[payload.target_type]} не найден(а)")

    own = (payload.target_type == "profile" and payload.target_id == user.id) or (
        payload.target_type != "profile" and author == user.login
    )
    if own:
        raise HTTPException(status.HTTP_409_CONFLICT, "Нельзя пожаловаться на свой материал")

    existing = await db.scalar(
        select(Report.id).where(
            Report.reporter_id == user.id,
            Report.target_type == payload.target_type,
            Report.target_id == payload.target_id,
        )
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Вы уже отправили жалобу на этот объект")

    report = Report(
        reporter_id=user.id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        reason=payload.reason,
        comment=payload.comment,
        status=REPORT_OPEN,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return await _to_read(db, report, user.login)


async def list_my_reports(db: AsyncSession, user: User) -> list[ReportRead]:
    reports = (
        await db.scalars(
            select(Report).where(Report.reporter_id == user.id).order_by(Report.created_at.desc())
        )
    ).all()
    return [await _to_read(db, r, user.login) for r in reports]


# --- Очередь жалоб (T4.2) ---


async def list_reports(
    db: AsyncSession,
    *,
    status_filter: str | None = None,
    target_type: str | None = None,
) -> list[ReportRead]:
    stmt = (
        select(Report, User.login)
        .join(User, User.id == Report.reporter_id)
        .order_by(Report.created_at.desc(), Report.id.desc())
    )
    if status_filter:
        stmt = stmt.where(Report.status == status_filter)
    if target_type:
        stmt = stmt.where(Report.target_type == target_type)
    rows = (await db.execute(stmt)).all()
    return [await _to_read(db, r, login) for r, login in rows]


async def _hide(
    db: AsyncSession, moderator: User, target_type: str, target_id: int, reason: str
) -> None:
    if target_type == "review":
        review = await db.get(Review, target_id)
        if review is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Рецензия не найдена")
        review.is_hidden = True
    elif target_type == "comment":
        comment = await db.get(Comment, target_id)
        if comment is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Комментарий не найден")
        comment.is_hidden = True
    elif target_type == "card":
        item = await db.get(CatalogItem, target_id)
        if item is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Карточка не найдена")
        item.moderation_status = MODERATION_HIDDEN
    else:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Скрыть можно только рецензию, комментарий или карточку. "
            "Жалобу на профиль можно отклонить",
        )
    audit.record(db, moderator, audit.CONTENT_HIDE, target_type, target_id, reason=reason)


async def _delete(
    db: AsyncSession, moderator: User, target_type: str, target_id: int, reason: str
) -> list[str]:
    files: list[str] = []
    if target_type == "review":
        review = await db.get(Review, target_id)
        if review is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Рецензия не найдена")
        await delete_reviews(db, [review.id])
    elif target_type == "comment":
        comment = await db.get(Comment, target_id)
        if comment is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Комментарий не найден")
        await delete_comments(db, [comment.id])
    elif target_type == "card":
        item = await db.get(CatalogItem, target_id)
        if item is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Карточка не найдена")
        files = await delete_card(db, item)
    else:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Удалить можно только рецензию, комментарий или карточку. "
            "Жалобу на профиль можно отклонить",
        )
    audit.record(db, moderator, audit.CONTENT_DELETE, target_type, target_id, reason=reason)
    return files


async def hide_content(
    db: AsyncSession, moderator: User, target_type: str, target_id: int, reason: str
) -> None:
    await _hide(db, moderator, target_type, target_id, reason)
    await _close_open_reports(db, moderator, target_type, target_id, "hide", reason)
    await db.commit()


async def delete_content(
    db: AsyncSession, moderator: User, target_type: str, target_id: int, reason: str
) -> None:
    files = await _delete(db, moderator, target_type, target_id, reason)
    await db.commit()
    for path in files:
        delete_image(path)


async def _close_open_reports(
    db: AsyncSession,
    moderator: User,
    target_type: str,
    target_id: int,
    resolution: str,
    reason: str,
) -> None:
    """Скрытие закрывает и остальные открытые жалобы на тот же материал."""
    await db.execute(
        update(Report)
        .where(
            Report.target_type == target_type,
            Report.target_id == target_id,
            Report.status == REPORT_OPEN,
        )
        .values(
            status=REPORT_RESOLVED,
            resolution=resolution,
            resolution_reason=reason,
            resolved_by=moderator.id,
            resolved_at=datetime.now(UTC),
        )
    )


async def resolve_report(
    db: AsyncSession,
    moderator: User,
    report_id: int,
    decision: str,
    reason: str | None = None,
) -> ReportRead:
    report = await db.get(Report, report_id)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Жалоба не найдена")
    if report.status != REPORT_OPEN:
        raise HTTPException(status.HTTP_409_CONFLICT, "Жалоба уже разобрана")
    if decision in ("hide", "delete") and not reason:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Укажите причину скрытия или удаления"
        )

    reporter_login = await db.scalar(select(User.login).where(User.id == report.reporter_id)) or ""
    target_type, target_id = report.target_type, report.target_id
    if decision == "reject":
        report.status = REPORT_CLOSED
        report.resolution = "reject"
        report.resolution_reason = reason
        report.resolved_by = moderator.id
        report.resolved_at = datetime.now(UTC)
        audit.record(
            db,
            moderator,
            audit.REPORT_RESOLVE,
            "report",
            report.id,
            decision="reject",
            reason=reason,
            target=f"{target_type}:{target_id}",
        )
    elif decision == "hide":
        await _hide(db, moderator, target_type, target_id, reason or "")
        await _close_open_reports(db, moderator, target_type, target_id, "hide", reason or "")
        audit.record(
            db,
            moderator,
            audit.REPORT_RESOLVE,
            "report",
            report.id,
            decision="hide",
            reason=reason,
            target=f"{target_type}:{target_id}",
        )
    else:  # delete
        # Жалобы на удалённый материал уходят вместе с ним, решение остаётся в журнале.
        snapshot = await _to_read(db, report, reporter_login)
        audit.record(
            db,
            moderator,
            audit.REPORT_RESOLVE,
            "report",
            report.id,
            decision="delete",
            reason=reason,
            target=f"{target_type}:{target_id}",
        )
        files = await _delete(db, moderator, target_type, target_id, reason or "")
        await db.commit()
        for path in files:
            delete_image(path)
        return snapshot.model_copy(
            update={
                "status": REPORT_RESOLVED,
                "resolution": "delete",
                "resolution_reason": reason,
                "resolved_by": moderator.id,
                "resolved_at": datetime.now(UTC),
            }
        )

    await db.commit()
    await db.refresh(report)
    return await _to_read(db, report, reporter_login)


# --- Очередь локальных карточек (T4.2) ---


async def list_pending_cards(db: AsyncSession) -> list[ModerationCardRead]:
    rows = (
        await db.execute(
            select(CatalogItem, User.login)
            .outerjoin(User, User.id == CatalogItem.created_by)
            .where(
                CatalogItem.source == SOURCE_LOCAL,
                CatalogItem.moderation_status == MODERATION_PENDING,
            )
            .order_by(CatalogItem.created_at.asc(), CatalogItem.id.asc())
        )
    ).all()
    result = []
    for item, login in rows:
        base = CatalogItemRead.model_validate(item).model_dump()
        result.append(
            ModerationCardRead(**base, moderation_status=item.moderation_status, author_login=login)
        )
    return result


async def _pending_card(db: AsyncSession, item_id: int) -> CatalogItem:
    item = await db.get(CatalogItem, item_id)
    if item is None or item.source != SOURCE_LOCAL:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Локальная карточка не найдена")
    if item.moderation_status != MODERATION_PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, "Карточка уже проверена")
    return item


async def approve_card(db: AsyncSession, moderator: User, item_id: int) -> None:
    item = await _pending_card(db, item_id)
    item.moderation_status = MODERATION_APPROVED
    audit.record(db, moderator, audit.CARD_APPROVE, "card", item.id, title=item.title)
    await db.commit()


async def reject_card(db: AsyncSession, moderator: User, item_id: int, reason: str) -> None:
    item = await _pending_card(db, item_id)
    item.moderation_status = MODERATION_HIDDEN
    audit.record(db, moderator, audit.CARD_REJECT, "card", item.id, title=item.title, reason=reason)
    await db.commit()
