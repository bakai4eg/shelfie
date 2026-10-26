"""Полки и оценки пользователя. Задачи T2.4, T3.3."""

from fastapi import APIRouter

router = APIRouter(prefix="/me", tags=["library"])

# TODO(T2.4): GET /library, PUT /library/{item_id}, DELETE /library/{item_id}
# TODO(T3.3): PUT /ratings/{item_id}, DELETE /ratings/{item_id}
# Контракт: docs/api.md, раздел 5.
