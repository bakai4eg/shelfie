"""Лайки рецензий и комментариев (ТЗ 4.5.3)."""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social import Comment, Like, Review
from app.models.user import User
from app.schemas.social import LikeState


async def like_counts(
    db: AsyncSession, target_type: str, ids: list[int], viewer: User | None
) -> dict[int, tuple[int, bool]]:
    """Счётчик и признак «лайкнул ли я» сразу для пачки объектов, без запроса на каждый."""
    if not ids:
        return {}
    counts = dict(
        (
            await db.execute(
                select(Like.target_id, func.count(Like.id))
                .where(Like.target_type == target_type, Like.target_id.in_(ids))
                .group_by(Like.target_id)
            )
        ).all()
    )
    mine: set[int] = set()
    if viewer is not None:
        mine = set(
            await db.scalars(
                select(Like.target_id).where(
                    Like.target_type == target_type,
                    Like.target_id.in_(ids),
                    Like.user_id == viewer.id,
                )
            )
        )
    return {i: (counts.get(i, 0), i in mine) for i in ids}


async def _ensure_target(db: AsyncSession, target_type: str, target_id: int) -> None:
    """Лайк на скрытый или несуществующий материал не принимается и не считается."""
    if target_type == "review":
        review = await db.get(Review, target_id)
        if review is None or review.is_hidden:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Рецензия не найдена")
        return
    comment = await db.get(Comment, target_id)
    if comment is None or comment.is_hidden:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Комментарий не найден")
    review = await db.get(Review, comment.review_id)
    if review is None or review.is_hidden:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Комментарий не найден")


async def _state(db: AsyncSession, user: User, target_type: str, target_id: int) -> LikeState:
    count, mine = (await like_counts(db, target_type, [target_id], user))[target_id]
    return LikeState(
        target_type=target_type, target_id=target_id, likes_count=count, liked_by_me=mine
    )


async def add_like(db: AsyncSession, user: User, target_type: str, target_id: int) -> LikeState:
    await _ensure_target(db, target_type, target_id)
    existing = await db.scalar(
        select(Like.id).where(
            Like.user_id == user.id, Like.target_type == target_type, Like.target_id == target_id
        )
    )
    if existing is None:  # повторный лайк идемпотентен: счётчик не растёт
        db.add(Like(user_id=user.id, target_type=target_type, target_id=target_id))
        await db.commit()
    return await _state(db, user, target_type, target_id)


async def remove_like(db: AsyncSession, user: User, target_type: str, target_id: int) -> LikeState:
    await _ensure_target(db, target_type, target_id)
    like = await db.scalar(
        select(Like).where(
            Like.user_id == user.id, Like.target_type == target_type, Like.target_id == target_id
        )
    )
    if like is not None:
        await db.delete(like)
        await db.commit()
    return await _state(db, user, target_type, target_id)
