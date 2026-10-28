"""Профили: публичная страница и статистика (T1.3, ТЗ 4.2.3)."""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ITEM_BOOK, ITEM_MOVIE, ITEM_SERIES, STATUS_FINISHED
from app.core.media import avatar_url, delete_avatar, save_avatar
from app.core.security import hash_password, verify_password
from app.models.catalog import CatalogItem
from app.models.library import Rating, ShelfEntry
from app.models.social import Follow, Review
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
    """Реальные данные статистики пользователя (ТЗ 4.2.3)."""
    # finished по типам
    books_read = await db.scalar(
        select(func.count(ShelfEntry.id))
        .join(CatalogItem, CatalogItem.id == ShelfEntry.item_id)
        .where(
            ShelfEntry.user_id == user.id,
            ShelfEntry.status == STATUS_FINISHED,
            CatalogItem.type == ITEM_BOOK,
        )
    ) or 0

    movies_watched = await db.scalar(
        select(func.count(ShelfEntry.id))
        .join(CatalogItem, CatalogItem.id == ShelfEntry.item_id)
        .where(
            ShelfEntry.user_id == user.id,
            ShelfEntry.status == STATUS_FINISHED,
            CatalogItem.type == ITEM_MOVIE,
        )
    ) or 0

    series_watched = await db.scalar(
        select(func.count(ShelfEntry.id))
        .join(CatalogItem, CatalogItem.id == ShelfEntry.item_id)
        .where(
            ShelfEntry.user_id == user.id,
            ShelfEntry.status == STATUS_FINISHED,
            CatalogItem.type == ITEM_SERIES,
        )
    ) or 0

    # оценки
    avg_val, count_val = (
        await db.execute(
            select(
                func.coalesce(func.avg(Rating.value), 0.0),
                func.count(Rating.id),
            ).where(Rating.user_id == user.id)
        )
    ).one()
    rating_avg = round(float(avg_val or 0.0), 2)
    ratings_count = int(count_val or 0)

    # рецензии
    reviews_count = await db.scalar(
        select(func.count(Review.id)).where(
            Review.user_id == user.id,
            Review.is_hidden.is_(False),
        )
    ) or 0

    # подписчики и подписки
    followers = await db.scalar(
        select(func.count(Follow.id)).where(Follow.following_id == user.id)
    ) or 0

    following = await db.scalar(
        select(func.count(Follow.id)).where(Follow.follower_id == user.id)
    ) or 0

    return UserStats(
        books_read=books_read,
        movies_watched=movies_watched,
        series_watched=series_watched,
        ratings_count=ratings_count,
        rating_avg=rating_avg,
        reviews_count=reviews_count,
        followers=followers,
        following=following,
    )


async def public_profile(
    db: AsyncSession,
    user: User,
    viewer: User | None = None,
) -> PublicProfile:
    following_target = False
    if viewer and viewer.id != user.id:
        is_fol = await db.scalar(
            select(Follow.id).where(
                Follow.follower_id == viewer.id,
                Follow.following_id == user.id,
            )
        )
        following_target = is_fol is not None

    return PublicProfile(
        login=user.login,
        avatar_url=avatar_url(user.avatar_path),
        bio=user.bio,
        registered_at=user.created_at,
        stats=await user_stats(db, user),
        is_following=following_target,
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
