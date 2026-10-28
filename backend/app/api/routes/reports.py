"""Жалобы пользователей (ТЗ 4.6.2)."""

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.moderation import ReportCreate, ReportRead
from app.services.moderation import create_report, list_my_reports

router = APIRouter(tags=["reports"])


@router.post(
    "/reports",
    response_model=ReportRead,
    status_code=status.HTTP_201_CREATED,
    summary="Отправить жалобу",
)
async def post_report(
    payload: ReportCreate,
    db: SessionDep,
    user: CurrentUser,
) -> ReportRead:
    return await create_report(db, user, payload)


@router.get(
    "/me/reports",
    response_model=list[ReportRead],
    summary="Мои жалобы",
)
async def get_my_reports(
    db: SessionDep,
    user: CurrentUser,
) -> list[ReportRead]:
    return await list_my_reports(db, user)
