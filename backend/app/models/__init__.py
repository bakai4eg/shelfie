"""ORM-модели, сгруппированные по подсистемам.

Правило: модель живёт в файле своей подсистемы, все модели импортируются
здесь, чтобы Alembic видел полную метадату (`Base.metadata`).
"""

from app.models.catalog import CatalogItem
from app.models.library import Rating, ShelfEntry
from app.models.moderation import Report
from app.models.social import Follow, Review
from app.models.user import Session, User

__all__ = [
    "CatalogItem",
    "Follow",
    "Rating",
    "Report",
    "Review",
    "Session",
    "ShelfEntry",
    "User",
]
