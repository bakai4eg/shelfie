"""Схемы полок и оценок (ТЗ 4.2.2, 4.4.1, 4.4.2)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.constants import RATING_MAX, RATING_MIN
from app.schemas.catalog import CatalogItemRead

ShelfStatus = Literal["watching", "finished", "planned", "dropped"]


class ShelfUpsert(BaseModel):
    status: ShelfStatus
    finished_at: date | None = None

    @model_validator(mode="after")
    def validate_finished_at(self) -> "ShelfUpsert":
        if self.status == "finished":
            if not self.finished_at:
                raise ValueError("Для статуса «finished» требуется дата завершения (finished_at)")
        else:
            self.finished_at = None
        return self


class ShelfEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    status: ShelfStatus
    finished_at: date | None = None
    item: CatalogItemRead
    user_rating: int | None = None
    created_at: datetime
    updated_at: datetime


class RatingUpsert(BaseModel):
    value: int = Field(ge=RATING_MIN, le=RATING_MAX)


class RatingResult(BaseModel):
    value: int
    rating_avg: float
    ratings_count: int
