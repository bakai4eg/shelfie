"""Схемы профиля. Контракт — docs/api.md, раздел 2."""

from datetime import datetime

from pydantic import BaseModel


class UserStats(BaseModel):
    """Статистика профиля. На этапе 1 поля есть, но считаются нулями.

    Полки появятся в T2.4, рецензии — в T4.3, подписки — в T5.4. Поля уже
    в контракте, чтобы фронтенд не переделывать: когда таблицы появятся,
    `services/profile.py` начнёт считать их реальными запросами.
    """

    books_read: int = 0
    movies_watched: int = 0
    series_watched: int = 0
    ratings_count: int = 0
    rating_avg: float = 0
    reviews_count: int = 0
    followers: int = 0
    following: int = 0


class PublicProfile(BaseModel):
    """Публичная страница: без e-mail, роли и служебных полей."""

    login: str
    avatar_url: str | None = None
    bio: str | None = None
    registered_at: datetime
    stats: UserStats
    is_following: bool = False


class ReviewPreview(BaseModel):
    """Карточка рецензии в профиле; наполнение — T4.3."""

    id: int
    title: str
    rating: int | None = None
    created_at: datetime


class ListPreview(BaseModel):
    """Публичный список в профиле; наполнение — T3.2."""

    id: int
    title: str
    theme: str = "classic"
    items_count: int = 0
