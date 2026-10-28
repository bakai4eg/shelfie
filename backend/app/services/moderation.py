"""Сервис жалоб и модерации (ТЗ 4.6.2, 4.6.3)."""

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import MODERATION_HIDDEN
from app.models.catalog import CatalogItem
from app.models.moderation import Report
from app.models.social import Review
from app.models.user import User
from app.schemas.moderation import ReportCreate, ReportRead


def _to_report_read(report: Report, reporter_login: str) -> ReportRead:
    return ReportRead(
        id=report.id,
        reporter_id=report.reporter_id,
        reporter_login=reporter_login,
        target_type=report.target_type,
        target_id=report.target_id,
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
    if payload.target_type == "comment":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Жалобы на комментарии пока не поддерживаются"
        )
    elif payload.target_type == "review":
        rev = await db.scalar(select(Review.id).where(Review.id == payload.target_id))
        if not rev:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Рецензия не найдена")
    elif payload.target_type == "card":
        card = await db.scalar(select(CatalogItem.id).where(CatalogItem.id == payload.target_id))
        if not card:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Карточка не найдена")
    elif payload.target_type == "profile":
        profile_user = await db.scalar(select(User.id).where(User.id == payload.target_id))
        if not profile_user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Профиль не найден")
    else:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Неизвестный тип объекта")

    existing = await db.scalar(
        select(Report.id).where(
            Report.reporter_id == user.id,
            Report.target_type == payload.target_type,
            Report.target_id == payload.target_id,
        )
    )
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Вы уже отправили жалобу на этот объект"
        )

    report = Report(
        reporter_id=user.id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        reason=payload.reason,
        comment=payload.comment,
        status="open",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return _to_report_read(report, user.login)


async def list_my_reports(db: AsyncSession, user: User) -> list[ReportRead]:
    stmt = (
        select(Report)
        .where(Report.reporter_id == user.id)
        .order_by(Report.created_at.desc())
    )
    reports = (await db.scalars(stmt)).all()
    return [_to_report_read(r, user.login) for r in reports]


async def list_reports(
    db: AsyncSession,
    *,
    status_filter: str | None = None,
    target_type: str | None = None,
) -> list[ReportRead]:
    stmt = (
        select(Report, User.login)
        .join(User, User.id == Report.reporter_id)
        .order_by(Report.created_at.desc())
    )
    if status_filter:
        stmt = stmt.where(Report.status == status_filter)
    if target_type:
        stmt = stmt.where(Report.target_type == target_type)

    rows = (await db.execute(stmt)).all()
    return [_to_report_read(r, login) for r, login in rows]


async def resolve_report(
    db: AsyncSession,
    moderator: User,
    report_id: int,
    decision: str,
    reason: str | None = None,
) -> ReportRead:
    report = await db.scalar(
        select(Report).where(Report.id == report_id).options(selectinload(Report.reporter))
    )
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Жалоба не найдена")

    now = datetime.now(UTC)
    report.resolution = decision
    report.resolution_reason = reason
    report.resolved_by = moderator.id
    report.resolved_at = now

    if decision in ("reject", "rejected"):
        report.status = "closed"
    elif decision in ("hide", "hidden"):
        report.status = "resolved"
        if report.target_type == "review":
            review = await db.scalar(select(Review).where(Review.id == report.target_id))
            if review:
                review.is_hidden = True
        elif report.target_type in ("card", "item"):
            item = await db.scalar(select(CatalogItem).where(CatalogItem.id == report.target_id))
            if item:
                item.moderation_status = MODERATION_HIDDEN
    elif decision in ("delete", "deleted"):
        report.status = "resolved"
        if report.target_type == "review":
            review = await db.scalar(select(Review).where(Review.id == report.target_id))
            if review:
                await db.delete(review)
        elif report.target_type in ("card", "item"):
            item = await db.scalar(select(CatalogItem).where(CatalogItem.id == report.target_id))
            if item:
                await db.delete(item)

    await db.commit()
    await db.refresh(report)
    reporter_login = report.reporter.login if report.reporter else "unknown"
    return _to_report_read(report, reporter_login)
