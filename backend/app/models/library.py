"""Полки и оценки (ТЗ 4.2.2, 4.4.1, 4.4.2)."""

from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ShelfEntry(Base, TimestampMixin):
    __tablename__ = "shelf_entries"
    __table_args__ = (
        UniqueConstraint("user_id", "item_id", name="uq_shelf_entries_user_item"),
        Index("ix_shelf_entries_user_id", "user_id"),
        Index("ix_shelf_entries_item_id", "item_id"),
        Index("ix_shelf_entries_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_items.id", ondelete="CASCADE"),
    )
    status: Mapped[str] = mapped_column(String(16))
    finished_at: Mapped[date | None] = mapped_column(Date)

    user: Mapped["User"] = relationship()  # noqa: F821
    item: Mapped["CatalogItem"] = relationship()  # noqa: F821


class Rating(Base, TimestampMixin):
    __tablename__ = "ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "item_id", name="uq_ratings_user_item"),
        CheckConstraint("value >= 1 AND value <= 10", name="ck_ratings_value_range"),
        Index("ix_ratings_user_id", "user_id"),
        Index("ix_ratings_item_id", "item_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_items.id", ondelete="CASCADE"),
    )
    value: Mapped[int] = mapped_column(Integer)

    user: Mapped["User"] = relationship()  # noqa: F821
    item: Mapped["CatalogItem"] = relationship()  # noqa: F821
