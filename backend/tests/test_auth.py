"""Регистрация, вход и сессии — ТЗ 4.2.1."""

import pytest

REGISTER = "/api/auth/register"
LOGIN = "/api/auth/login"
LOGOUT = "/api/auth/logout"
ME = "/api/auth/me"

USER = {"login": "bakai", "email": "bakai@example.com", "password": "password123"}


def register(client, **overrides):
    return client.post(REGISTER, json={**USER, **overrides})


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_register_returns_token_and_user(client):
    response = register(client)

    assert response.status_code == 201
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["expires_at"]
    assert data["user"] == {
        "id": data["user"]["id"],
        "login": "bakai",
        "email": "bakai@example.com",
        "role": "user",
    }
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]

    me = client.get(ME, headers=headers(data["access_token"]))
    assert me.status_code == 200
    assert me.json()["login"] == "bakai"


def test_register_normalizes_email(client):
    data = register(client, email="Bakai@Example.COM").json()

    assert data["user"]["email"] == "bakai@example.com"


def test_register_rejects_duplicate_login(client):
    register(client)

    response = register(client, email="other@example.com")

    assert response.status_code == 409
    assert response.json()["detail"] == "Логин уже занят"


def test_register_rejects_duplicate_email_ignoring_case(client):
    register(client)

    response = register(client, login="other", email="BAKAI@example.com")

    assert response.status_code == 409
    assert response.json()["detail"] == "E-mail уже занят"


@pytest.mark.parametrize(
    "overrides",
    [
        {"login": "ab"},
        {"login": "bad login"},
        {"login": "bad-login"},
        {"password": "short"},
        {"password": "x" * 73},
        {"email": "not-an-email"},
        {"email": "no@dot"},
    ],
)
def test_register_validates_input(client, overrides):
    response = register(client, **overrides)

    assert response.status_code == 422


@pytest.mark.parametrize("identifier", ["bakai", "bakai@example.com", "BAKAI@EXAMPLE.COM"])
def test_login_accepts_login_or_email(client, identifier):
    register(client)

    response = client.post(LOGIN, json={"login": identifier, "password": USER["password"]})

    assert response.status_code == 200
    assert response.json()["user"]["login"] == "bakai"


def test_login_rejects_wrong_password(client):
    register(client)

    response = client.post(LOGIN, json={"login": "bakai", "password": "wrong-password"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Неверный логин или пароль"


def test_login_rejects_unknown_user(client):
    response = client.post(LOGIN, json={"login": "nobody", "password": "password123"})

    assert response.status_code == 401


def test_logout_revokes_only_current_session(client):
    first = register(client).json()
    second = client.post(
        LOGIN, json={"login": "bakai", "password": USER["password"]}
    ).json()

    logout = client.post(LOGOUT, headers=headers(first["access_token"]))
    assert logout.status_code == 204

    assert client.get(ME, headers=headers(first["access_token"])).status_code == 401
    assert client.get(ME, headers=headers(second["access_token"])).status_code == 200

    again = client.post(LOGOUT, headers=headers(first["access_token"]))
    assert again.status_code == 401


def test_me_requires_token(client):
    response = client.get(ME)

    assert response.status_code == 401
    assert response.json()["detail"] == "Не авторизован"


def test_garbage_token_is_rejected(client):
    response = client.get(ME, headers=headers("not-a-jwt"))

    assert response.status_code == 401
