"""Матрица доступа: гость, авторизованный пользователь, блокировка — ТЗ 4.2.2."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — регистрирует модели в Base.metadata
from app.api.deps import get_current_auth, require_admin, require_moderator
from app.core.constants import ROLE_ADMIN, ROLE_MODERATOR, ROLE_USER
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.models.user import Session as AuthSession
from app.models.user import User

PROTECTED = [
    ("GET", "/api/auth/me"),
    ("POST", "/api/auth/logout"),
]

PUBLIC = [
    ("GET", "/api/health"),
    ("GET", "/docs"),
]


def register(client, login="bakai"):
    response = client.post(
        "/api/auth/register",
        json={
            "login": login,
            "email": f"{login}@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 201
    return response.json()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_guest_gets_401(client, method, path):
    response = client.request(method, path)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(("method", "path"), PUBLIC)
def test_guest_reads_public_endpoints(client, method, path):
    assert client.request(method, path).status_code == 200


def test_user_gets_access_with_token(client):
    token = register(client)["access_token"]

    assert client.get("/api/auth/me", headers=bearer(token)).status_code == 200
    assert client.post("/api/auth/logout", headers=bearer(token)).status_code == 204


@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def add_user(db, *, login="blocked", blocked=False) -> User:
    user = User(
        login=login,
        email=f"{login}@example.com",
        password_hash=hash_password("password123"),
        is_blocked=blocked,
    )
    db.add(user)
    await db.flush()
    return user


async def add_session(
    db,
    user: User,
    *,
    expired: bool = False,
    revoked: bool = False,
) -> str:
    jti = str(uuid4())
    now = datetime.now(UTC)
    db.add(
        AuthSession(
            user_id=user.id,
            jti=jti,
            expires_at=now - timedelta(minutes=1) if expired else now + timedelta(hours=1),
            revoked_at=now if revoked else None,
        )
    )
    await db.commit()
    return create_access_token(subject=str(user.id), jti=jti, role=user.role)


def credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


async def test_blocked_user_gets_403(db):
    user = await add_user(db, blocked=True)
    token = await add_session(db, user)

    with pytest.raises(HTTPException) as error:
        await get_current_auth(credentials(token), db)

    assert error.value.status_code == 403
    assert error.value.detail == "Аккаунт заблокирован"


async def test_expired_session_gets_401(db):
    user = await add_user(db)
    token = await add_session(db, user, expired=True)

    with pytest.raises(HTTPException) as error:
        await get_current_auth(credentials(token), db)

    assert error.value.status_code == 401


async def test_revoked_session_gets_401(db):
    user = await add_user(db)
    token = await add_session(db, user, revoked=True)

    with pytest.raises(HTTPException) as error:
        await get_current_auth(credentials(token), db)

    assert error.value.status_code == 401


async def test_require_role_matrix():
    plain = User(role=ROLE_USER)
    moderator = User(role=ROLE_MODERATOR)
    admin = User(role=ROLE_ADMIN)

    assert await require_moderator(moderator) is moderator
    assert await require_moderator(admin) is admin
    assert await require_admin(admin) is admin

    for checker, user in (
        (require_moderator, plain),
        (require_admin, plain),
        (require_admin, moderator),
    ):
        with pytest.raises(HTTPException) as error:
            await checker(user)
        assert error.value.status_code == 403
