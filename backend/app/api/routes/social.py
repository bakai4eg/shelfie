"""Рецензии и подписки (ТЗ 4.2.3, 4.5.1, 4.5.4)."""

from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.common import Page
from app.schemas.social import FollowState, ReviewCreate, ReviewRead, ReviewUpdate, UserShort
from app.services.social import (
    create_review,
    delete_review,
    follow_user,
    list_followers,
    list_following,
    list_reviews,
    unfollow_user,
    update_review,
)

router = APIRouter(tags=["social"])


@router.get(
    "/catalog/{item_id}/reviews",
    response_model=Page[ReviewRead],
    summary="Рецензии на карточку",
)
async def get_item_reviews(
    item_id: int,
    db: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[ReviewRead]:
    return await list_reviews(db, item_id, page=page, size=size)


@router.post(
    "/catalog/{item_id}/reviews",
    response_model=ReviewRead,
    status_code=status.HTTP_201_CREATED,
    summary="Написать рецензию",
)
async def post_item_review(
    item_id: int,
    payload: ReviewCreate,
    db: SessionDep,
    user: CurrentUser,
) -> ReviewRead:
    return await create_review(db, user, item_id, payload)


@router.patch(
    "/reviews/{review_id}",
    response_model=ReviewRead,
    summary="Редактировать рецензию",
)
async def patch_review(
    review_id: int,
    payload: ReviewUpdate,
    db: SessionDep,
    user: CurrentUser,
) -> ReviewRead:
    return await update_review(db, user, review_id, payload)


@router.delete(
    "/reviews/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить рецензию",
)
async def remove_review(
    review_id: int,
    db: SessionDep,
    user: CurrentUser,
) -> Response:
    await delete_review(db, user, review_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/users/{login}/follow",
    response_model=FollowState,
    summary="Подписаться на пользователя",
)
async def follow(
    login: str,
    db: SessionDep,
    user: CurrentUser,
) -> FollowState:
    return await follow_user(db, user, login)


@router.delete(
    "/users/{login}/follow",
    response_model=FollowState,
    summary="Отписаться от пользователя",
)
async def unfollow(
    login: str,
    db: SessionDep,
    user: CurrentUser,
) -> FollowState:
    return await unfollow_user(db, user, login)


@router.get(
    "/users/{login}/followers",
    response_model=list[UserShort],
    summary="Подписчики пользователя",
)
async def get_followers(
    login: str,
    db: SessionDep,
) -> list[UserShort]:
    return await list_followers(db, login)


@router.get(
    "/users/{login}/following",
    response_model=list[UserShort],
    summary="Подписки пользователя",
)
async def get_following(
    login: str,
    db: SessionDep,
) -> list[UserShort]:
    return await list_following(db, login)
