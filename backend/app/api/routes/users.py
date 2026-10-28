"""Профили: публичная страница и её разделы (T1.3)."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import OptionalUser, SessionDep
from app.schemas.common import Page
from app.schemas.profile import ListPreview, PublicProfile, ReviewPreview
from app.services.profile import get_user_by_login, public_profile

router = APIRouter(tags=["users"])


@router.get("/users/{login}", response_model=PublicProfile, summary="Публичный профиль")
async def get_profile(login: str, db: SessionDep, viewer: OptionalUser) -> PublicProfile:
    user = await get_user_by_login(db, login)
    return await public_profile(db, user, viewer)


@router.get(
    "/users/{login}/reviews",
    response_model=Page[ReviewPreview],
    summary="Публичные рецензии пользователя",
)
async def get_user_reviews(
    login: str,
    db: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[ReviewPreview]:
    # Пользователь должен существовать: иначе 404, а не пустой список.
    await get_user_by_login(db, login)
    # TODO(T4.3): выборка рецензий; до появления модели отдаём пустую страницу.
    return Page[ReviewPreview](items=[], total=0, page=page, size=size)


@router.get(
    "/users/{login}/lists",
    response_model=Page[ListPreview],
    summary="Публичные списки пользователя",
)
async def get_user_lists(
    login: str,
    db: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[ListPreview]:
    await get_user_by_login(db, login)
    # TODO(T3.2): выборка публичных списков; до появления модели — пусто.
    return Page[ListPreview](items=[], total=0, page=page, size=size)
