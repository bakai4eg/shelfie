"""Комментарии к рецензиям (ТЗ 4.5.2)."""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ROLE_ADMIN, ROLE_MODERATOR
from app.core.media import avatar_url
from app.models.social import Comment, Review
from app.models.user import User
from app.schemas.common import Page
from app.schemas.social import CommentRead
from app.services import audit
from app.services.cleanup import delete_comments
from app.services.likes import like_counts


def _is_moderator(user: User | None) -> bool:
    return user is not None and user.role in (ROLE_MODERATOR, ROLE_ADMIN)


async def _readable_review(db: AsyncSession, review_id: int, viewer: User | None) -> Review:
    """Скрытая рецензия прячет и свои комментарии: её видят только автор и модератор."""
    review = await db.get(Review, review_id)
    if review is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Рецензия не найдена")
    if review.is_hidden and not (
        _is_moderator(viewer) or (viewer is not None and viewer.id == review.user_id)
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Рецензия не найдена")
    return review


async def list_comments(
    db: AsyncSession, review_id: int, viewer: User | None, page: int, size: int
) -> Page[CommentRead]:
    review = await _readable_review(db, review_id, viewer)
    # Скрытая рецензия не отдаёт комментарии никому: обсуждать там нечего.
    if review.is_hidden:
        return Page[CommentRead](items=[], total=0, page=page, size=size)

    condition = (Comment.review_id == review_id, Comment.is_hidden.is_(False))
    total = await db.scalar(select(func.count()).select_from(Comment).where(*condition)) or 0
    rows = (
        await db.execute(
            select(Comment, User)
            .join(User, User.id == Comment.user_id)
            .where(*condition)
            .order_by(Comment.created_at.asc(), Comment.id.asc())
            .offset((page - 1) * size)
            .limit(size)
        )
    ).all()
    likes = await like_counts(db, "comment", [c.id for c, _ in rows], viewer)
    items = [
        CommentRead(
            id=c.id,
            review_id=c.review_id,
            user_login=u.login,
            user_avatar_url=avatar_url(u.avatar_path),
            body=c.body,
            likes_count=likes[c.id][0],
            liked_by_me=likes[c.id][1],
            created_at=c.created_at,
        )
        for c, u in rows
    ]
    return Page[CommentRead](items=items, total=total, page=page, size=size)


async def create_comment(db: AsyncSession, user: User, review_id: int, body: str) -> CommentRead:
    review = await _readable_review(db, review_id, user)
    if review.is_hidden:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Рецензия не найдена")
    comment = Comment(review_id=review_id, user_id=user.id, body=body)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return CommentRead(
        id=comment.id,
        review_id=review_id,
        user_login=user.login,
        user_avatar_url=avatar_url(user.avatar_path),
        body=comment.body,
        created_at=comment.created_at,
    )


async def remove_comment(db: AsyncSession, user: User, comment_id: int) -> None:
    comment = await db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Комментарий не найден")
    own = comment.user_id == user.id
    if not own and not _is_moderator(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Удалять может только автор или модератор")
    if not own:
        audit.record(
            db, user, audit.CONTENT_DELETE, "comment", comment.id, reason="удалено модератором"
        )
    await delete_comments(db, [comment.id])
    await db.commit()
