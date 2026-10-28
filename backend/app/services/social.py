"""Сервис рецензий и подписок (ТЗ 4.2.3, 4.5.1, 4.5.4)."""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import ROLE_ADMIN, ROLE_MODERATOR
from app.core.media import avatar_url as media_url
from app.models.social import Follow, Review
from app.models.user import User
from app.schemas.common import Page
from app.schemas.social import FollowState, ReviewCreate, ReviewRead, ReviewUpdate, UserShort
from app.services.library import get_visible_item


def _to_review_read(review: Review, user: User) -> ReviewRead:
    return ReviewRead(
        id=review.id,
        item_id=review.item_id,
        user_login=user.login,
        user_avatar_url=media_url(user.avatar_path),
        title=review.title,
        body=review.body,
        rating=review.rating,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


async def list_reviews(
    db: AsyncSession, item_id: int, page: int = 1, size: int = 20
) -> Page[ReviewRead]:
    base = (
        select(Review, User)
        .join(User, User.id == Review.user_id)
        .where(Review.item_id == item_id, Review.is_hidden.is_(False))
    )
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    stmt = (
        base.order_by(Review.created_at.desc(), Review.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = (await db.execute(stmt)).all()
    items = [_to_review_read(rev, u) for rev, u in rows]
    return Page[ReviewRead](items=items, total=total, page=page, size=size)


async def create_review(
    db: AsyncSession, user: User, item_id: int, payload: ReviewCreate
) -> ReviewRead:
    item = await get_visible_item(db, item_id, user)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Карточка не найдена")

    existing = await db.scalar(
        select(Review.id).where(Review.user_id == user.id, Review.item_id == item_id)
    )
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Вы уже написали рецензию на эту карточку"
        )

    review = Review(
        user_id=user.id,
        item_id=item_id,
        title=payload.title.strip(),
        body=payload.body.strip(),
        rating=payload.rating,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return _to_review_read(review, user)


async def update_review(
    db: AsyncSession, user: User, review_id: int, payload: ReviewUpdate
) -> ReviewRead:
    review = await db.scalar(
        select(Review).where(Review.id == review_id).options(selectinload(Review.user))
    )
    if not review:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Рецензия не найдена")
    if review.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Редактировать может только автор")

    if payload.title is not None:
        review.title = payload.title.strip()
    if payload.body is not None:
        review.body = payload.body.strip()
    if payload.rating is not None:
        review.rating = payload.rating

    await db.commit()
    await db.refresh(review)
    return _to_review_read(review, user)


async def delete_review(db: AsyncSession, user: User, review_id: int) -> None:
    review = await db.scalar(select(Review).where(Review.id == review_id))
    if not review:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Рецензия не найдена")

    is_moderator = user.role in (ROLE_MODERATOR, ROLE_ADMIN)
    if review.user_id != user.id and not is_moderator:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Удалять может только автор или модератор")

    await db.delete(review)
    await db.commit()


async def list_user_reviews(
    db: AsyncSession, login: str, page: int = 1, size: int = 20
) -> Page[ReviewRead]:
    author = await db.scalar(select(User).where(func.lower(User.login) == login.lower()))
    if not author:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")

    base = (
        select(Review)
        .where(Review.user_id == author.id, Review.is_hidden.is_(False))
    )
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    stmt = (
        base.order_by(Review.created_at.desc(), Review.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    reviews = list((await db.scalars(stmt)).all())
    items = [_to_review_read(r, author) for r in reviews]
    return Page[ReviewRead](items=items, total=total, page=page, size=size)


async def follow_user(db: AsyncSession, user: User, target_login: str) -> FollowState:
    target = await db.scalar(select(User).where(func.lower(User.login) == target_login.lower()))
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
    if target.id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Нельзя подписаться на самого себя")

    existing = await db.scalar(
        select(Follow).where(Follow.follower_id == user.id, Follow.following_id == target.id)
    )
    if not existing:
        db.add(Follow(follower_id=user.id, following_id=target.id))
        await db.commit()

    followers = await followers_count(db, target.id)
    following = await following_count(db, target.id)
    return FollowState(is_following=True, followers=followers, following=following)


async def unfollow_user(db: AsyncSession, user: User, target_login: str) -> FollowState:
    target = await db.scalar(select(User).where(func.lower(User.login) == target_login.lower()))
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
    if target.id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Нельзя отписаться от самого себя")

    existing = await db.scalar(
        select(Follow).where(Follow.follower_id == user.id, Follow.following_id == target.id)
    )
    if existing:
        await db.delete(existing)
        await db.commit()

    followers = await followers_count(db, target.id)
    following = await following_count(db, target.id)
    return FollowState(is_following=False, followers=followers, following=following)


async def is_following(db: AsyncSession, viewer: User | None, target_id: int) -> bool:
    if not viewer:
        return False
    val = await db.scalar(
        select(Follow.id).where(Follow.follower_id == viewer.id, Follow.following_id == target_id)
    )
    return val is not None


async def followers_count(db: AsyncSession, user_id: int) -> int:
    return await db.scalar(
        select(func.count(Follow.id)).where(Follow.following_id == user_id)
    ) or 0


async def following_count(db: AsyncSession, user_id: int) -> int:
    return await db.scalar(
        select(func.count(Follow.id)).where(Follow.follower_id == user_id)
    ) or 0


async def list_followers(db: AsyncSession, login: str) -> list[UserShort]:
    user = await db.scalar(select(User).where(func.lower(User.login) == login.lower()))
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
    stmt = (
        select(User)
        .join(Follow, Follow.follower_id == User.id)
        .where(Follow.following_id == user.id)
        .order_by(Follow.created_at.desc())
    )
    followers = (await db.scalars(stmt)).all()
    return [
        UserShort(login=u.login, avatar_url=media_url(u.avatar_path), bio=u.bio)
        for u in followers
    ]


async def list_following(db: AsyncSession, login: str) -> list[UserShort]:
    user = await db.scalar(select(User).where(func.lower(User.login) == login.lower()))
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
    stmt = (
        select(User)
        .join(Follow, Follow.following_id == User.id)
        .where(Follow.follower_id == user.id)
        .order_by(Follow.created_at.desc())
    )
    following = (await db.scalars(stmt)).all()
    return [
        UserShort(login=u.login, avatar_url=media_url(u.avatar_path), bio=u.bio)
        for u in following
    ]
