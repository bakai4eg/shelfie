"""Модерация: жалобы пользователей (ТЗ 4.6.2, 4.6.3)."""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Report(Base, TimestampMixin):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint(
            "reporter_id", "target_type", "target_id", name="uq_reports_reporter_target"
        ),
        Index("ix_reports_reporter_id", "reporter_id"),
        Index("ix_reports_target_type", "target_type"),
        Index("ix_reports_target_id", "target_id"),
        Index("ix_reports_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    target_type: Mapped[str] = mapped_column(String(16))
    target_id: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(32))
    comment: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="open", server_default="open")
    resolution: Mapped[str | None] = mapped_column(String(16))
    resolution_reason: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    reporter: Mapped["User"] = relationship(foreign_keys=[reporter_id])  # noqa: F821
    resolver: Mapped["User | None"] = relationship(foreign_keys=[resolved_by])  # noqa: F821
