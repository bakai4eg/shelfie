"""Общие схемы ответов: пагинация и простые сообщения.

Все списочные эндпоинты возвращают `Page[T]`, чтобы фронтенд не писал
свой формат под каждый раздел (docs/api.md, «Общие правила»).
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    size: int = 20


class Message(BaseModel):
    detail: str
