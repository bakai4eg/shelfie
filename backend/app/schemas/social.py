"""Схемы рецензий и подписок (ТЗ 4.2.3, 4.5.1, 4.5.4)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import (
    COMMENT_MAX_LENGTH,
    RATING_MAX,
    RATING_MIN,
    REVIEW_BODY_MAX_LENGTH,
)


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
    item_title: str | None = None
    user_login: str
    user_avatar_url: str | None = None
    title: str
    body: str
    rating: int | None = None
    is_hidden: bool = False
    comments_count: int = 0
    likes_count: int = 0
    liked_by_me: bool = False
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


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=COMMENT_MAX_LENGTH)

    @field_validator("body")
    @classmethod
    def strip_body(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Комментарий не может быть пустым")
        return value


class CommentRead(BaseModel):
    id: int
    review_id: int
    user_login: str
    user_avatar_url: str | None = None
    body: str
    likes_count: int = 0
    liked_by_me: bool = False
    created_at: datetime


class LikeTarget(BaseModel):
    target_type: Literal["review", "comment"]
    target_id: int


class LikeState(BaseModel):
    target_type: str
    target_id: int
    likes_count: int
    liked_by_me: bool


class FeedItemRef(BaseModel):
    id: int
    title: str
    type: str | None = None
    poster_url: str | None = None


class FeedEvent(BaseModel):
    id: int
    event_type: Literal["review_created", "item_finished", "rating_set", "list_published"]
    created_at: datetime
    user: UserShort
    item: FeedItemRef | None = None
    review: FeedItemRef | None = None
    list: FeedItemRef | None = None
    value: int | None = None
