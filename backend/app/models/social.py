"""Рецензии и подписки (ТЗ 4.2.3, 4.5.1, 4.5.4)."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Review(Base, TimestampMixin):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("user_id", "item_id", name="uq_reviews_user_item"),
        Index("ix_reviews_user_id", "user_id"),
        Index("ix_reviews_item_id", "item_id"),
        Index("ix_reviews_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_items.id", ondelete="CASCADE"),
    )
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    rating: Mapped[int | None] = mapped_column(Integer)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())

    user: Mapped["User"] = relationship()  # noqa: F821
    item: Mapped["CatalogItem"] = relationship()  # noqa: F821


class Follow(Base, TimestampMixin):
    __tablename__ = "follows"
    __table_args__ = (
        UniqueConstraint("follower_id", "following_id", name="uq_follows_follower_following"),
        CheckConstraint("follower_id != following_id", name="ck_follows_no_self_follow"),
        Index("ix_follows_follower_id", "follower_id"),
        Index("ix_follows_following_id", "following_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    follower_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    following_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )

    follower: Mapped["User"] = relationship(foreign_keys=[follower_id])  # noqa: F821
    following: Mapped["User"] = relationship(foreign_keys=[following_id])  # noqa: F821


class Comment(Base, TimestampMixin):
    """Комментарий под рецензией (ТЗ 4.5.2)."""

    __tablename__ = "comments"
    __table_args__ = (
        Index("ix_comments_review_id", "review_id"),
        Index("ix_comments_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    body: Mapped[str] = mapped_column(String(1000))
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())

    user: Mapped["User"] = relationship()  # noqa: F821


class Like(Base):
    """Лайк рецензии или комментария (ТЗ 4.5.3). Цель полиморфная: тип + id."""

    __tablename__ = "likes"
    __table_args__ = (
        UniqueConstraint("user_id", "target_type", "target_id", name="uq_likes_user_target"),
        Index("ix_likes_target", "target_type", "target_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    target_type: Mapped[str] = mapped_column(String(16))
    target_id: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ActivityEvent(Base):
    """Событие ленты активности (ТЗ 4.5.4)."""

    __tablename__ = "activity_events"
    __table_args__ = (
        Index("ix_activity_events_user_id", "user_id"),
        Index("ix_activity_events_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(24))
    item_id: Mapped[int | None] = mapped_column(ForeignKey("catalog_items.id", ondelete="CASCADE"))
    review_id: Mapped[int | None] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"))
    list_id: Mapped[int | None] = mapped_column(ForeignKey("lists.id", ondelete="CASCADE"))
    value: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship()  # noqa: F821
