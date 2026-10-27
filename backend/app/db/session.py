"""Асинхронный движок и фабрика сессий."""

import json
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


def json_serializer(value: object) -> str:
    """JSON с ensure_ascii=False: жанры и подписи ищем по тексту, а не по escape-кодам."""
    return json.dumps(value, ensure_ascii=False)


engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    json_serializer=json_serializer,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Зависимость FastAPI: одна сессия на запрос, коммит — на стороне сервиса."""
    async with SessionLocal() as session:
        yield session
