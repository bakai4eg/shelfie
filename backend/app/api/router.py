"""Сборка всех роутеров API.

Порядок и префиксы соответствуют `docs/api.md`. Новый модуль подсистемы —
новый файл в `routes/` и одна строка `include_router` здесь.
"""

from fastapi import APIRouter

from app.api.routes import (
    admin,
    auth,
    catalog,
    health,
    library,
    lists,
    moderation,
    social,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(catalog.router)
api_router.include_router(library.router)
api_router.include_router(lists.router)
api_router.include_router(social.router)
api_router.include_router(moderation.router)
api_router.include_router(admin.router)
