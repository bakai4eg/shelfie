"""Профили: публичная страница и статистика (T1.3, ТЗ 4.2.3)."""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.media import avatar_url, delete_avatar, save_avatar
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.profile import ProfileUpdate, PublicProfile, UserStats
from app.services.auth import revoke_all_sessions

USER_NOT_FOUND = "Пользователь не найден"
INVALID_CURRENT_PASSWORD = "Неверный текущий пароль"


async def get_user_by_login(db: AsyncSession, login: str) -> User:
    """Логин в URL регистронезависимый: /u/Bakai и /u/bakai — один профиль."""
    needle = login.strip().lower()
    user = await db.scalar(select(User).where(func.lower(User.login) == needle).limit(1))
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, USER_NOT_FOUND)
    return user


async def user_stats(db: AsyncSession, user: User) -> UserStats:
    """Заглушка до появления полок, оценок, рецензий и подписок.

    TODO(T2.4): books_read / movies_watched / series_watched из `user_items`.
    TODO(T3.3): ratings_count и rating_avg — только по выставленным оценкам.
    TODO(T4.3): reviews_count из `reviews`.
    TODO(T5.4): followers / following из `follows`.
    Средняя считается как сумма/количество; при нуле оценок — 0.0, без деления.
    """
    return UserStats()


async def public_profile(
    db: AsyncSession,
    user: User,
    viewer: User | None = None,
) -> PublicProfile:
    return PublicProfile(
        login=user.login,
        avatar_url=avatar_url(user.avatar_path),
        bio=user.bio,
        registered_at=user.created_at,
        stats=await user_stats(db, user),
        # TODO(T5.4): подписки появятся вместе с таблицей follows.
        is_following=False,
    )


async def update_bio(db: AsyncSession, user: User, payload: ProfileUpdate) -> PublicProfile:
    """PATCH: если поле не передали — не трогаем; пустая строка очищает."""
    if "bio" in payload.model_fields_set:
        user.bio = payload.bio
        await db.commit()
        await db.refresh(user)
    return await public_profile(db, user, user)


async def set_avatar(db: AsyncSession, user: User, data: bytes, content_type: str) -> str:
    """Сохраняет новый файл и удаляет старый. В БД — относительный путь."""
    relative = save_avatar(data, content_type)
    delete_avatar(user.avatar_path)
    user.avatar_path = relative
    await db.commit()
    await db.refresh(user)
    return avatar_url(relative) or ""


async def remove_avatar(db: AsyncSession, user: User) -> None:
    delete_avatar(user.avatar_path)
    user.avatar_path = None
    await db.commit()


async def change_password(
    db: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    """После смены пароля отзываем все сессии, включая текущую (ТЗ 4.2.4)."""
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, INVALID_CURRENT_PASSWORD)

    user.password_hash = hash_password(new_password)
    await db.commit()
    await revoke_all_sessions(db, user.id)
