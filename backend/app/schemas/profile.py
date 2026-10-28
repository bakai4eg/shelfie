"""Схемы профиля. Контракт — docs/api.md, раздел 2."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.constants import BIO_MAX_LENGTH, PASSWORD_MIN_LENGTH

PASSWORD_MAX_BYTES = 72


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


class ProfileUpdate(BaseModel):
    """PATCH /me/profile. Пустая строка и null одинаково очищают описание."""

    bio: str | None = Field(default=None, max_length=BIO_MAX_LENGTH)

    @field_validator("bio")
    @classmethod
    def normalize_bio(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=128)

    @field_validator("new_password")
    @classmethod
    def check_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > PASSWORD_MAX_BYTES:
            raise ValueError(f"Пароль длиннее {PASSWORD_MAX_BYTES} байт")
        return value

    @model_validator(mode="after")
    def check_differs(self) -> "PasswordChange":
        if self.new_password == self.current_password:
            raise ValueError("Новый пароль совпадает с текущим")
        return self


class AvatarResponse(BaseModel):
    avatar_url: str
