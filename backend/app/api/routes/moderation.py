"""Модерация: очередь жалоб и их разрешение (ТЗ 4.6.3)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import SessionDep, require_moderator
from app.models.user import User
from app.schemas.moderation import ReportRead, ReportResolve
from app.services.moderation import list_reports, resolve_report

router = APIRouter(prefix="/moderation", tags=["moderation"])

ModeratorUser = Annotated[User, Depends(require_moderator)]


@router.get("/reports", response_model=list[ReportRead], summary="Очередь жалоб")
async def get_moderation_reports(
    db: SessionDep,
    _moderator: ModeratorUser,
    status: str | None = None,
    target_type: str | None = None,
) -> list[ReportRead]:
    return await list_reports(db, status_filter=status, target_type=target_type)


@router.post(
    "/reports/{report_id}/resolve",
    response_model=ReportRead,
    summary="Решение по жалобе",
)
async def resolve_moderation_report(
    report_id: int,
    payload: ReportResolve,
    db: SessionDep,
    moderator: ModeratorUser,
) -> ReportRead:
    return await resolve_report(
        db,
        moderator,
        report_id,
        decision=payload.decision,
        reason=payload.reason,
    )
