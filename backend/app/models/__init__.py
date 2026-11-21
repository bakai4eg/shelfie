"""ORM-модели, сгруппированные по подсистемам.

Правило: модель живёт в файле своей подсистемы, все модели импортируются
здесь, чтобы Alembic видел полную метадату (`Base.metadata`).
"""

from app.models.audit import AuditLog
from app.models.catalog import CatalogItem
from app.models.library import Rating, ShelfEntry
from app.models.lists import ListItem, UserList
from app.models.moderation import Report
from app.models.social import ActivityEvent, Comment, Follow, Like, Review
from app.models.user import Session, User

__all__ = [
    "ActivityEvent",
    "Comment",
    "Like",
    "AuditLog",
    "CatalogItem",
    "Follow",
    "ListItem",
    "Rating",
    "Report",
    "Review",
    "Session",
    "ShelfEntry",
    "User",
    "UserList",
]
