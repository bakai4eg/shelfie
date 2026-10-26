"""Стартовая точка API.

Роутеры подсистем подключаются здесь. Пустые модули в `api/routes/` —
места под задачи этапов, их не нужно создавать заново.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Схему БД создаём миграциями Alembic, а не здесь.
    yield
    await engine.dispose()


app = FastAPI(
    title="Shelfie API",
    version="0.1.0",
    description="Социальная медиа-платформа и каталог рецензий медиа-контента",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
