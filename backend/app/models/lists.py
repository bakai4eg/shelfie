"""Пользовательские списки-витрины (ТЗ 4.4.3)."""

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import LIST_NOTE_MAX_LENGTH
from app.db.base import Base, TimestampMixin


class UserList(Base, TimestampMixin):
    __tablename__ = "lists"
    __table_args__ = (Index("ix_lists_user_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(String(1000))
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    theme: Mapped[str] = mapped_column(String(16), default="classic", server_default="classic")

    user: Mapped["User"] = relationship()  # noqa: F821
    items: Mapped[list["ListItem"]] = relationship(
        back_populates="list",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ListItem.position",
    )


class ListItem(Base, TimestampMixin):
    __tablename__ = "list_items"
    __table_args__ = (
        UniqueConstraint("list_id", "item_id", name="uq_list_items_list_item"),
        Index("ix_list_items_list_id", "list_id"),
        Index("ix_list_items_item_id", "item_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    list_id: Mapped[int] = mapped_column(ForeignKey("lists.id", ondelete="CASCADE"))
    item_id: Mapped[int] = mapped_column(ForeignKey("catalog_items.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str | None] = mapped_column(String(LIST_NOTE_MAX_LENGTH))

    list: Mapped[UserList] = relationship(back_populates="items")
    item: Mapped["CatalogItem"] = relationship()  # noqa: F821
