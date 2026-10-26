"""Администрирование. Задачи T5.1–T5.2."""

from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])

# TODO(T5.1): GET /users, PATCH /users/{user_id}/role,
#             POST /users/{user_id}/block|unblock, DELETE /users/{user_id}
# TODO(T5.2): GET /summary, GET /audit
# Контракт: docs/api.md, раздел 11.
