"""Схемы списков-витрин. Контракт — docs/api.md, раздел 6."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import LIST_NOTE_MAX_LENGTH
from app.schemas.catalog import CatalogItemRead

ListTheme = Literal["classic", "noir", "pastel"]


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


class ListCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    is_public: bool = False
    theme: ListTheme = "classic"

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Название не может быть пустым")
        return value

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str | None) -> str | None:
        return _clean(value)


class ListUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    is_public: bool | None = None
    theme: ListTheme | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Название не может быть пустым")
        return value


class ListItemAdd(BaseModel):
    item_id: int
    note: str | None = Field(default=None, max_length=LIST_NOTE_MAX_LENGTH)

    @field_validator("note")
    @classmethod
    def strip_note(cls, value: str | None) -> str | None:
        return _clean(value)


class ListItemUpdate(BaseModel):
    note: str | None = Field(default=None, max_length=LIST_NOTE_MAX_LENGTH)

    @field_validator("note")
    @classmethod
    def strip_note(cls, value: str | None) -> str | None:
        return _clean(value)


class ListOrder(BaseModel):
    item_ids: list[int]


class ListItemRead(BaseModel):
    position: int
    note: str | None = None
    item: CatalogItemRead


class ListSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    is_public: bool
    theme: ListTheme
    items_count: int = 0
    created_at: datetime
    updated_at: datetime


class ListOwner(BaseModel):
    login: str
    avatar_url: str | None = None


class ListDetail(ListSummary):
    owner: ListOwner
    items: list[ListItemRead] = Field(default_factory=list)
