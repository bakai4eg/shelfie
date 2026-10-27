"""Каталог: книги, фильмы и сериалы (ТЗ 4.3.1).

Одна таблица на все типы контента: тип, источник и статус проверки — строки
из `core.constants`, чтобы SQLite в тестах и PostgreSQL в проде вели себя
одинаково. `genres` храним как JSON-список, а не отдельной таблицей: жанры
не редактируются отдельно от карточки.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    event,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import (
    ITEM_TYPES,
    MODERATION_APPROVED,
    SOURCE_LOCAL,
)
from app.db.base import Base, TimestampMixin

TITLE_MAX_LENGTH = 500
COUNTRY_MAX_LENGTH = 100
EXTERNAL_ID_MAX_LENGTH = 64
POSTER_PATH_MAX_LENGTH = 255


class CatalogItem(Base, TimestampMixin):
    __tablename__ = "catalog_items"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_catalog_items_source_external_id"),
        Index("ix_catalog_items_type", "type"),
        Index("ix_catalog_items_year", "year"),
        Index("ix_catalog_items_is_local", "is_local"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(
        String(32), default=SOURCE_LOCAL, server_default=SOURCE_LOCAL
    )
    external_id: Mapped[str | None] = mapped_column(String(EXTERNAL_ID_MAX_LENGTH))
    title: Mapped[str] = mapped_column(String(TITLE_MAX_LENGTH))
    original_title: Mapped[str | None] = mapped_column(String(TITLE_MAX_LENGTH))
    # lower(title + original_title), заполняется перед вставкой/обновлением.
    # Нужен, потому что SQLite не умеет lower() для кириллицы, а поиск
    # регистронезависимый и в тестах, и в проде.
    title_normalized: Mapped[str] = mapped_column(String(1000), default="", index=True)
    year: Mapped[int | None] = mapped_column(Integer)
    country: Mapped[str | None] = mapped_column(String(COUNTRY_MAX_LENGTH))
    genres: Mapped[list[str]] = mapped_column(JSON, default=list)
    description: Mapped[str | None] = mapped_column(Text)
    poster_path: Mapped[str | None] = mapped_column(String(POSTER_PATH_MAX_LENGTH))
    is_local: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    moderation_status: Mapped[str] = mapped_column(
        String(16), default=MODERATION_APPROVED, server_default=MODERATION_APPROVED
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    rating_avg: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), default=Decimal("0"), server_default="0"
    )
    ratings_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:  # pragma: no cover — только для отладки
        return f"<CatalogItem {self.type}:{self.id} {self.title!r}>"


@event.listens_for(CatalogItem, "before_insert")
@event.listens_for(CatalogItem, "before_update")
def _fill_title_normalized(mapper, connection, target: CatalogItem) -> None:
    """Держим поисковую строку в актуальном состоянии без триггеров БД."""
    target.title_normalized = f"{target.title} {target.original_title or ''}".strip().lower()

# Типы вынесены наружу для валидации и сидов, чтобы не дублировать кортеж.
CATALOG_TYPES = ITEM_TYPES
