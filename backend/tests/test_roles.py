"""Роли и права доступа (ТЗ 4.6.1, T3.1): пользователь, модератор, администратор."""

import asyncio

import pytest

from app.core.constants import ROLE_ADMIN, ROLE_MODERATOR, ROLE_USER
from app.db.session import get_session
from app.main import app
from app.models.user import User
from app.scripts import set_role as set_role_script

API = "/api"

# (метод, путь, минимальная роль). Дальше: гость → 401, ниже роли → 403, достаточная → не 401/403.
MATRIX = [
    ("GET", f"{API}/me/lists", ROLE_USER),
    ("GET", f"{API}/auth/me", ROLE_USER),
    ("GET", f"{API}/moderation/reports", ROLE_MODERATOR),
]


def register(client, login: str) -> tuple[int, dict[str, str]]:
    res = client.post(
        f"{API}/auth/register",
        json={"login": login, "email": f"{login}@example.com", "password": "secret123"},
    )
    assert res.status_code == 201, res.text
    return res.json()["user"]["id"], {"Authorization": f"Bearer {res.json()['access_token']}"}


def give_role(user_id: int, role: str) -> None:
    async def _set():
        async for session in app.dependency_overrides[get_session]():
            user = await session.get(User, user_id)
            user.role = role
            await session.commit()
            return

    asyncio.run(_set())


@pytest.mark.parametrize(("method", "path", "minimum"), MATRIX)
def test_guest_gets_401(client, method, path, minimum):
    assert client.request(method, path).status_code == 401


@pytest.mark.parametrize("role", [ROLE_USER, ROLE_MODERATOR, ROLE_ADMIN])
@pytest.mark.parametrize(("method", "path", "minimum"), MATRIX)
def test_access_by_role_level(client, method, path, minimum, role):
    user_id, headers = register(client, "someone")
    give_role(user_id, role)

    levels = {ROLE_USER: 1, ROLE_MODERATOR: 2, ROLE_ADMIN: 3}
    res = client.request(method, path, headers=headers)

    if levels[role] < levels[minimum]:
        assert res.status_code == 403
        assert res.json()["detail"] == "Недостаточно прав"
    else:
        assert res.status_code == 200, res.text


def test_role_is_read_from_db_not_from_token(client):
    user_id, headers = register(client, "grower")
    url = f"{API}/moderation/reports"

    assert client.get(url, headers=headers).status_code == 403
    give_role(user_id, ROLE_MODERATOR)  # тот же токен, роль поменялась только в БД
    assert client.get(url, headers=headers).status_code == 200
    give_role(user_id, ROLE_USER)
    assert client.get(url, headers=headers).status_code == 403


def test_set_role_script_changes_role(client, monkeypatch):
    user_id, _ = register(client, "devuser")

    async def fake_set(login: str, role: str) -> str:
        async for session in app.dependency_overrides[get_session]():
            from sqlalchemy import select

            user = await session.scalar(select(User).where(User.login == login))
            user.role = role
            await session.commit()
            return f"@{login}: ok"
        return ""

    monkeypatch.setattr(set_role_script, "set_role", fake_set)
    assert set_role_script.main(["devuser", "admin"]) == 0

    async def _read():
        async for session in app.dependency_overrides[get_session]():
            return (await session.get(User, user_id)).role

    assert asyncio.run(_read()) == ROLE_ADMIN


def test_set_role_script_rejects_unknown_role():
    with pytest.raises(SystemExit):
        set_role_script.main(["someone", "superuser"])
