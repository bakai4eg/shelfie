"""Схемы жалоб и модерации (ТЗ 4.6.2, 4.6.3)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.catalog import CatalogItemRead

TargetType = Literal["review", "comment", "card", "profile"]
ReportReason = Literal["spam", "insult", "false_info", "copyright", "other"]
ReportDecision = Literal["reject", "hide", "delete"]
ContentType = Literal["review", "card"]

EXPLANATION_MAX_LENGTH = 1000


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


class ReportCreate(BaseModel):
    target_type: TargetType
    target_id: int
    reason: ReportReason
    comment: str | None = Field(default=None, max_length=EXPLANATION_MAX_LENGTH)

    @field_validator("comment")
    @classmethod
    def strip_comment(cls, value: str | None) -> str | None:
        return _clean(value)

    @model_validator(mode="after")
    def other_needs_explanation(self) -> "ReportCreate":
        if self.reason == "other" and not self.comment:
            raise ValueError("Для причины «иное» нужно текстовое пояснение")
        return self


class ReportResolve(BaseModel):
    decision: ReportDecision
    reason: str | None = Field(default=None, max_length=EXPLANATION_MAX_LENGTH)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str | None) -> str | None:
        return _clean(value)


class ContentAction(BaseModel):
    """Причина скрытия или удаления фиксируется всегда (ТЗ 4.6.3)."""

    reason: str = Field(min_length=1, max_length=EXPLANATION_MAX_LENGTH)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Укажите причину")
        return value


class CardReject(BaseModel):
    reason: str = Field(min_length=1, max_length=EXPLANATION_MAX_LENGTH)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Укажите причину")
        return value


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reporter_id: int
    reporter_login: str
    target_type: str
    target_id: int
    # Контекст для модератора: что за материал и кто его автор.
    target_title: str | None = None
    target_author: str | None = None
    reason: str
    comment: str | None = None
    status: str
    resolution: str | None = None
    resolution_reason: str | None = None
    resolved_by: int | None = None
    resolved_at: datetime | None = None
    created_at: datetime


class ModerationCardRead(CatalogItemRead):
    moderation_status: str
    author_login: str | None = None
