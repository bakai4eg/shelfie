"""Тестовые фикстуры.

Тесты идут на SQLite в памяти, чтобы не требовать PostgreSQL (ТЗ 5.1).
Схему создаём лениво — в том же event loop, в котором работает приложение.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — регистрирует модели в Base.metadata
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_session
from app.main import app


@pytest.fixture(autouse=True)
def disable_external_providers():
    old = settings.enable_external_providers
    settings.enable_external_providers = False
    yield
    settings.enable_external_providers = old


@pytest.fixture
def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    schema_ready = False

    async def override_session():
        nonlocal schema_ready
        if not schema_ready:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            schema_ready = True
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
