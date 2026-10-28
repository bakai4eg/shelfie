"""Схемы рецензий и подписок (ТЗ 4.2.3, 4.5.1, 4.5.4)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import RATING_MAX, RATING_MIN, REVIEW_BODY_MAX_LENGTH


class ReviewCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=REVIEW_BODY_MAX_LENGTH)
    rating: int | None = Field(default=None, ge=RATING_MIN, le=RATING_MAX)


class ReviewUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, min_length=1, max_length=REVIEW_BODY_MAX_LENGTH)
    rating: int | None = Field(default=None, ge=RATING_MIN, le=RATING_MAX)


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    user_login: str
    user_avatar_url: str | None = None
    title: str
    body: str
    rating: int | None = None
    created_at: datetime
    updated_at: datetime


class UserShort(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    login: str
    avatar_url: str | None = None
    bio: str | None = None


class FollowState(BaseModel):
    is_following: bool
    followers: int
    following: int
