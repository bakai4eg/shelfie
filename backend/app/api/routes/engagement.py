"""Комментарии, лайки и лента (ТЗ 4.5.2-4.5.4). Контракт: docs/api.md, разделы 7-8."""

from typing import Annotated

from fastapi import APIRouter, Body, Query, Response, status

from app.api.deps import CurrentUser, OptionalUser, SessionDep
from app.schemas.common import Page
from app.schemas.social import CommentCreate, CommentRead, FeedEvent, LikeState, LikeTarget
from app.services import activity, comments, likes

router = APIRouter(tags=["engagement"])


@router.get(
    "/reviews/{review_id}/comments", response_model=Page[CommentRead], summary="Комментарии"
)
async def get_comments(
    review_id: int,
    db: SessionDep,
    viewer: OptionalUser,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[CommentRead]:
    return await comments.list_comments(db, review_id, viewer, page, size)


@router.post(
    "/reviews/{review_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Оставить комментарий",
)
async def post_comment(
    review_id: int, payload: CommentCreate, db: SessionDep, user: CurrentUser
) -> CommentRead:
    return await comments.create_comment(db, user, review_id, payload.body)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить комментарий",
)
async def delete_comment(comment_id: int, db: SessionDep, user: CurrentUser) -> Response:
    await comments.remove_comment(db, user, comment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/likes", response_model=LikeState, summary="Поставить лайк")
async def post_like(
    payload: Annotated[LikeTarget, Body()], db: SessionDep, user: CurrentUser
) -> LikeState:
    return await likes.add_like(db, user, payload.target_type, payload.target_id)


@router.delete("/likes", response_model=LikeState, summary="Снять лайк")
async def delete_like(
    payload: Annotated[LikeTarget, Body()], db: SessionDep, user: CurrentUser
) -> LikeState:
    return await likes.remove_like(db, user, payload.target_type, payload.target_id)


@router.get("/feed", response_model=Page[FeedEvent], summary="Лента активности подписок")
async def get_feed(
    db: SessionDep,
    user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> Page[FeedEvent]:
    return await activity.feed(db, user, page, size)
