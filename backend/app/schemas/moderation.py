"""Схемы жалоб и модерации (ТЗ 4.6.2, 4.6.3)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TargetType = Literal["review", "comment", "card", "profile"]
ReportReason = Literal["spam", "insult", "false_info", "copyright", "other"]
ReportResolution = Literal["reject", "hide", "delete"]


class ReportCreate(BaseModel):
    target_type: TargetType
    target_id: int
    reason: str = Field(min_length=1, max_length=32)
    comment: str | None = None


class ReportResolve(BaseModel):
    decision: ReportResolution
    reason: str | None = None


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reporter_id: int
    reporter_login: str
    target_type: str
    target_id: int
    reason: str
    comment: str | None = None
    status: str
    resolution: str | None = None
    resolution_reason: str | None = None
    resolved_by: int | None = None
    resolved_at: datetime | None = None
    created_at: datetime
