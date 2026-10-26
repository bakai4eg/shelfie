"""Профили: публичная страница, статистика, настройки. Задачи T1.3, T1.4, T2.3."""

from fastapi import APIRouter

router = APIRouter(tags=["users"])

# TODO(T1.3): GET /users/{login}, GET /users/{login}/reviews, GET /users/{login}/lists
# TODO(T1.4): PATCH /me/profile, POST /me/avatar, DELETE /me/avatar, PUT /me/password
# TODO(T5.4): POST /users/{login}/follow, DELETE /users/{login}/follow,
#             GET /users/{login}/followers, GET /users/{login}/following
# Контракт: docs/api.md, разделы 2 и 8.
