"""Локальные карточки сообщества (T2.3, ТЗ 4.3.3)."""

import asyncio

from app.core.config import settings
from app.core.constants import (
    MODERATION_APPROVED,
    MODERATION_HIDDEN,
    MODERATION_PENDING,
    ROLE_MODERATOR,
)
from app.db.session import get_session
from app.main import app
from app.models.catalog import CatalogItem

API = "/api"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def register(client, login: str = "elvina") -> dict:
    response = client.post(
        f"{API}/auth/register",
        json={"login": login, "email": f"{login.lower()}@example.com", "password": "secret123"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_card(
    client,
    headers: dict[str, str],
    *,
    title: str = "Манас",
    year: str = "2010",
    poster: bool = True,
):
    data = {
        "type": "movie",
        "title": title,
        "original_title": "Manas",
        "year": year,
        "country": "Кыргызстан",
        "genres": "эпос, история",
        "description": "Фильм о богатыре Манасе.",
        "is_local": "true",
    }
    files = {"poster": ("poster.png", PNG, "image/png")} if poster else None
    return client.post(f"{API}/cards/local", data=data, files=files, headers=headers)


def add_card(
    title: str = "Манас",
    year: int | None = 2010,
    mod_status: str = MODERATION_APPROVED,
) -> int:
    async def _add():
        async for session in app.dependency_overrides[get_session]():
            item = CatalogItem(
                type="book",
                title=title,
                year=year,
                is_local=True,
                genres=[],
                moderation_status=mod_status,
            )
            session.add(item)
            await session.commit()
            await session.refresh(item)
            return item.id

    return asyncio.run(_add())


def set_moderation(item_id: int, mod_status: str) -> None:
    async def _set():
        async for session in app.dependency_overrides[get_session]():
            item = await session.get(CatalogItem, item_id)
            assert item is not None
            item.moderation_status = mod_status
            await session.commit()

    asyncio.run(_set())


def test_guest_cannot_use_local_cards(client):
    created = client.post(
        f"{API}/cards/local", data={"type": "book", "title": "Манас"}
    )
    assert created.status_code == 401
    assert client.get(f"{API}/cards/local/mine").status_code == 401
    assert client.get(f"{API}/cards/local/duplicates", params={"title": "Манас"}).status_code == 401
    assert client.patch(f"{API}/cards/local/1", data={"title": "Новое"}).status_code == 401


def test_create_local_card_with_cover_and_visibility(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "media_root", str(tmp_path))
    author = register(client, "author")
    headers = auth(author["access_token"])
    moderator = register(client, "moder")
    moderator_headers = auth(moderator["access_token"])

    # Роль модератора выдаём напрямую в БД.
    async def promote() -> None:
        from app.models.user import User

        async for session in app.dependency_overrides[get_session]():
            user = await session.get(User, moderator["user"]["id"])
            assert user is not None
            user.role = ROLE_MODERATOR
            await session.commit()

    asyncio.run(promote())

    response = create_card(client, headers)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["source"] == "local"
    assert body["moderation_status"] == MODERATION_PENDING
    assert body["is_local"] is True
    assert body["title"] == "Манас"
    assert body["genres"] == ["эпос", "история"]
    assert body["poster_url"].startswith("/media/posters/")

    poster_path = tmp_path / body["poster_url"].removeprefix("/media/")
    assert poster_path.read_bytes() == PNG

    # Гость и другие пользователи не видят pending, автор и модератор — видят.
    assert client.get(f"{API}/catalog/{body['id']}").status_code == 404
    other = register(client, "other")
    assert (
        client.get(
            f"{API}/catalog/{body['id']}", headers=auth(other["access_token"])
        ).status_code
        == 404
    )
    assert client.get(f"{API}/catalog/{body['id']}", headers=headers).status_code == 200
    assert (
        client.get(f"{API}/catalog/{body['id']}", headers=moderator_headers).status_code
        == 200
    )


def test_mine_lists_only_own_cards(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "media_root", str(tmp_path))
    first = register(client, "first")
    second = register(client, "second")
    h1 = auth(first["access_token"])
    h2 = auth(second["access_token"])

    created = create_card(client, h1, title="Курманжан датка")
    assert created.status_code == 201, created.text

    mine = client.get(f"{API}/cards/local/mine", headers=h1)
    assert mine.status_code == 200
    assert mine.json()["total"] == 1
    assert mine.json()["items"][0]["title"] == "Курманжан датка"
    assert mine.json()["items"][0]["moderation_status"] == MODERATION_PENDING

    empty = client.get(f"{API}/cards/local/mine", headers=h2)
    assert empty.status_code == 200
    assert empty.json()["total"] == 0


def test_duplicates_are_suggested_before_creation(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "media_root", str(tmp_path))
    author = register(client, "author")
    headers = auth(author["access_token"])
    approved_id = add_card("Манас", year=2010)
    other_year_id = add_card("Манас", year=1995)

    response = client.get(
        f"{API}/cards/local/duplicates",
        params={"title": "манас", "year": 2010},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    items = response.json()
    assert [item["id"] for item in items] == [approved_id, other_year_id]
    assert items[0]["year"] == 2010

    # Посторонние pending-карточки в подсказки не попадают.
    stranger = register(client, "stranger")
    stranger_headers = auth(stranger["access_token"])
    pending = create_card(client, stranger_headers, title="Манас")
    assert pending.status_code == 201
    items = client.get(
        f"{API}/cards/local/duplicates",
        params={"title": "Манас"},
        headers=headers,
    ).json()
    assert pending.json()["id"] not in {item["id"] for item in items}


def test_patch_local_card_rules(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "media_root", str(tmp_path))
    author = register(client, "author")
    headers = auth(author["access_token"])
    other = register(client, "other")
    other_headers = auth(other["access_token"])

    created = create_card(client, headers)
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]
    first_poster = tmp_path / created.json()["poster_url"].removeprefix("/media/")

    # Автор правит карточку и меняет обложку.
    updated = client.patch(
        f"{API}/cards/local/{item_id}",
        data={"title": "Манас. Великий поход", "genres": '["эпос", "драма"]'},
        files={"poster": ("new.png", PNG, "image/png")},
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["title"] == "Манас. Великий поход"
    assert updated.json()["genres"] == ["эпос", "драма"]
    assert updated.json()["poster_url"] != created.json()["poster_url"]
    assert not first_poster.exists(), "старая обложка должна удаляться"

    # Чужую карточку править нельзя.
    forbidden = client.patch(
        f"{API}/cards/local/{item_id}",
        data={"title": "Взлом"},
        headers=other_headers,
    )
    assert forbidden.status_code == 404

    # После проверки правка закрыта.
    set_moderation(item_id, MODERATION_APPROVED)
    locked = client.patch(
        f"{API}/cards/local/{item_id}",
        data={"title": "Ещё правка"},
        headers=headers,
    )
    assert locked.status_code == 409
    assert "проверена" in locked.json()["detail"]


def test_create_validates_title_and_cover(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "media_root", str(tmp_path))
    author = register(client, "author")
    headers = auth(author["access_token"])

    blank = client.post(
        f"{API}/cards/local",
        data={"type": "book", "title": "   "},
        headers=headers,
    )
    assert blank.status_code == 422

    wrong_cover = client.post(
        f"{API}/cards/local",
        data={"type": "book", "title": "Книга"},
        files={"poster": ("cover.gif", b"GIF89a", "image/gif")},
        headers=headers,
    )
    assert wrong_cover.status_code == 422

    too_many_genres = client.post(
        f"{API}/cards/local",
        data={"type": "book", "title": "Книга", "genres": ",".join(f"жанр{i}" for i in range(21))},
        headers=headers,
    )
    assert too_many_genres.status_code == 422


def test_locked_hidden_card_is_not_editable(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "media_root", str(tmp_path))
    author = register(client, "author")
    headers = auth(author["access_token"])
    created = create_card(client, headers)
    item_id = created.json()["id"]
    set_moderation(item_id, MODERATION_HIDDEN)

    response = client.patch(
        f"{API}/cards/local/{item_id}",
        data={"title": "Нельзя"},
        headers=headers,
    )
    assert response.status_code == 409
