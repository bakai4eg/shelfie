"""Профили: публичная страница и статистика (T1.3, ТЗ 4.2.3)."""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.media import avatar_url
from app.models.user import User
from app.schemas.profile import PublicProfile, UserStats

USER_NOT_FOUND = "Пользователь не найден"


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
