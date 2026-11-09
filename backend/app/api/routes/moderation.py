"""Модерация: очереди, решения по жалобам, скрытие и удаление (ТЗ 4.6.3)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import SessionDep, require_moderator
from app.models.user import User
from app.schemas.moderation import (
    CardReject,
    ContentAction,
    ContentType,
    ModerationCardRead,
    ReportRead,
    ReportResolve,
)
from app.services import moderation as service

router = APIRouter(prefix="/moderation", tags=["moderation"])

ModeratorUser = Annotated[User, Depends(require_moderator)]


@router.get("/reports", response_model=list[ReportRead], summary="Очередь жалоб")
async def get_moderation_reports(
    db: SessionDep,
    _moderator: ModeratorUser,
    status: str | None = None,
    target_type: str | None = None,
) -> list[ReportRead]:
    return await service.list_reports(db, status_filter=status, target_type=target_type)


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
    return await service.resolve_report(
        db, moderator, report_id, decision=payload.decision, reason=payload.reason
    )


@router.post(
    "/content/{target_type}/{target_id}/hide",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Скрыть материал",
)
async def hide_moderation_content(
    target_type: ContentType,
    target_id: int,
    payload: ContentAction,
    db: SessionDep,
    moderator: ModeratorUser,
) -> Response:
    await service.hide_content(db, moderator, target_type, target_id, payload.reason)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/content/{target_type}/{target_id}/delete",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить материал с каскадом",
)
async def delete_moderation_content(
    target_type: ContentType,
    target_id: int,
    payload: ContentAction,
    db: SessionDep,
    moderator: ModeratorUser,
) -> Response:
    await service.delete_content(db, moderator, target_type, target_id, payload.reason)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/cards",
    response_model=list[ModerationCardRead],
    summary="Локальные карточки на проверке",
)
async def get_moderation_cards(
    db: SessionDep, _moderator: ModeratorUser
) -> list[ModerationCardRead]:
    return await service.list_pending_cards(db)


@router.post(
    "/cards/{item_id}/approve",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Подтвердить карточку",
)
async def approve_moderation_card(
    item_id: int, db: SessionDep, moderator: ModeratorUser
) -> Response:
    await service.approve_card(db, moderator, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/cards/{item_id}/reject",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отклонить карточку",
)
async def reject_moderation_card(
    item_id: int, payload: CardReject, db: SessionDep, moderator: ModeratorUser
) -> Response:
    await service.reject_card(db, moderator, item_id, payload.reason)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
