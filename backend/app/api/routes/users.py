"""Профили: публичная страница (T1.3) и настройки (T1.4)."""

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile, status

from app.api.deps import CurrentUser, OptionalUser, SessionDep
from app.core.config import settings
from app.schemas.common import Page
from app.schemas.profile import (
    AvatarResponse,
    ListPreview,
    PasswordChange,
    ProfileUpdate,
    PublicProfile,
    ReviewPreview,
)
from app.services.profile import (
    change_password,
    get_user_by_login,
    public_profile,
    remove_avatar,
    set_avatar,
    update_bio,
)

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


@router.patch("/me/profile", response_model=PublicProfile, summary="Описание профиля")
async def update_my_profile(
    payload: ProfileUpdate,
    db: SessionDep,
    user: CurrentUser,
) -> PublicProfile:
    return await update_bio(db, user, payload)


@router.post("/me/avatar", response_model=AvatarResponse, summary="Загрузить аватар")
async def upload_my_avatar(
    db: SessionDep,
    user: CurrentUser,
    file: Annotated[UploadFile, File(description="JPEG, PNG или WebP")],
) -> AvatarResponse:
    limit = settings.max_upload_size_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Файл больше {settings.max_upload_size_mb} МБ",
        )
    return AvatarResponse(avatar_url=await set_avatar(db, user, data, file.content_type or ""))


@router.delete("/me/avatar", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить аватар")
async def delete_my_avatar(db: SessionDep, user: CurrentUser) -> Response:
    await remove_avatar(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT, summary="Сменить пароль")
async def change_my_password(
    payload: PasswordChange,
    db: SessionDep,
    user: CurrentUser,
) -> Response:
    await change_password(db, user, payload.current_password, payload.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
