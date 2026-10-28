"""Настройки профиля: био, аватар, смена пароля (T1.4)."""

from app.core.config import settings

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
API = "/api"


def register(client, login: str = "elvina") -> dict:
    response = client.post(
        f"{API}/auth/register",
        json={"login": login, "email": f"{login.lower()}@example.com", "password": "secret123"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_guest_cannot_edit_profile(client):
    assert client.patch(f"{API}/me/profile", json={"bio": "привет"}).status_code == 401
    assert client.put(
        f"{API}/me/password",
        json={"current_password": "secret123", "new_password": "nextpass123"},
    ).status_code == 401


def test_bio_is_trimmed_saved_and_cleared(client):
    created = register(client)
    headers = auth(created["access_token"])

    updated = client.patch(f"{API}/me/profile", json={"bio": "  Читаю и смотрю  "}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["bio"] == "Читаю и смотрю"

    # PATCH без поля не затирает описание.
    untouched = client.patch(f"{API}/me/profile", json={}, headers=headers)
    assert untouched.json()["bio"] == "Читаю и смотрю"

    cleared = client.patch(f"{API}/me/profile", json={"bio": "   "}, headers=headers)
    assert cleared.json()["bio"] is None

    profile = client.get(f"{API}/users/{created['user']['login']}")
    assert profile.json()["bio"] is None


def test_bio_length_is_limited(client):
    created = register(client)
    headers = auth(created["access_token"])

    response = client.patch(f"{API}/me/profile", json={"bio": "я" * 501}, headers=headers)

    assert response.status_code == 422


def test_avatar_upload_replace_and_delete(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "media_root", str(tmp_path))
    created = register(client)
    headers = auth(created["access_token"])

    first = client.post(
        f"{API}/me/avatar",
        files={"file": ("avatar.png", PNG, "image/png")},
        headers=headers,
    )
    assert first.status_code == 200, first.text
    first_url = first.json()["avatar_url"]
    assert first_url.startswith("/media/avatars/")
    first_path = tmp_path / first_url.removeprefix("/media/")
    assert first_path.read_bytes() == PNG

    # Аватар сразу виден в /auth/me — его показывает шапка сайта.
    me = client.get(f"{API}/auth/me", headers=headers)
    assert me.json()["avatar_url"] == first_url

    second = client.post(
        f"{API}/me/avatar",
        files={"file": ("avatar.png", PNG, "image/png")},
        headers=headers,
    )
    second_url = second.json()["avatar_url"]
    second_path = tmp_path / second_url.removeprefix("/media/")
    assert second_url != first_url
    assert not first_path.exists(), "старый файл должен удаляться"
    assert second_path.exists()

    profile = client.get(f"{API}/users/{created['user']['login']}")
    assert profile.json()["avatar_url"] == second_url

    deleted = client.delete(f"{API}/me/avatar", headers=headers)
    assert deleted.status_code == 204
    assert not second_path.exists()
    assert client.get(f"{API}/auth/me", headers=headers).json()["avatar_url"] is None


def test_avatar_rejects_wrong_type_and_size(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "media_root", str(tmp_path))
    created = register(client)
    headers = auth(created["access_token"])

    wrong_type = client.post(
        f"{API}/me/avatar",
        files={"file": ("avatar.gif", b"GIF89a", "image/gif")},
        headers=headers,
    )
    assert wrong_type.status_code == 422
    assert "JPEG" in wrong_type.json()["detail"]

    fake_image = client.post(
        f"{API}/me/avatar",
        files={"file": ("avatar.png", b"not really a png", "image/png")},
        headers=headers,
    )
    assert fake_image.status_code == 422
    assert fake_image.json()["detail"] == "Файл не похож на изображение"

    empty = client.post(
        f"{API}/me/avatar",
        files={"file": ("avatar.png", b"", "image/png")},
        headers=headers,
    )
    assert empty.status_code == 422

    monkeypatch.setattr(settings, "max_upload_size_mb", 0)
    oversized = client.post(
        f"{API}/me/avatar",
        files={"file": ("avatar.png", PNG, "image/png")},
        headers=headers,
    )
    assert oversized.status_code == 422
    assert "МБ" in oversized.json()["detail"]


def test_password_change_revokes_sessions(client):
    created = register(client)
    token = created["access_token"]
    headers = auth(token)

    wrong = client.put(
        f"{API}/me/password",
        json={"current_password": "wrongpass", "new_password": "nextpass123"},
        headers=headers,
    )
    assert wrong.status_code == 400
    assert wrong.json()["detail"] == "Неверный текущий пароль"

    changed = client.put(
        f"{API}/me/password",
        json={"current_password": "secret123", "new_password": "nextpass123"},
        headers=headers,
    )
    assert changed.status_code == 204

    assert client.get(f"{API}/auth/me", headers=headers).status_code == 401
    assert (
        client.post(
            f"{API}/auth/login",
            json={"login": "elvina", "password": "secret123"},
        ).status_code
        == 401
    )

    login = client.post(
        f"{API}/auth/login",
        json={"login": "elvina", "password": "nextpass123"},
    )
    assert login.status_code == 200
    new_headers = auth(login.json()["access_token"])
    assert client.get(f"{API}/auth/me", headers=new_headers).status_code == 200


def test_password_change_validates_input(client):
    created = register(client)
    headers = auth(created["access_token"])

    short = client.put(
        f"{API}/me/password",
        json={"current_password": "secret123", "new_password": "short"},
        headers=headers,
    )
    assert short.status_code == 422

    same = client.put(
        f"{API}/me/password",
        json={"current_password": "secret123", "new_password": "secret123"},
        headers=headers,
    )
    assert same.status_code == 422
