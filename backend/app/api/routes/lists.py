"""Списки-витрины. Задача T3.2."""

from fastapi import APIRouter

router = APIRouter(tags=["lists"])

# TODO(T3.2): GET/POST /me/lists, GET/PATCH/DELETE /me/lists/{list_id}
#             POST/PATCH/DELETE /me/lists/{list_id}/items, PUT /me/lists/{list_id}/order
#             GET /public/lists/{list_id} — публичная витрина
# Контракт: docs/api.md, раздел 6.
