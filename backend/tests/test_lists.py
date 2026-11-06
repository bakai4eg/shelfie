"""Списки-витрины: порядок, заметки, приватность (ТЗ 4.4.3, T3.2)."""

import asyncio

import pytest

from app.core.constants import MODERATION_APPROVED, MODERATION_HIDDEN
from app.db.session import get_session
from app.main import app
from app.models.catalog import CatalogItem

API = "/api"


def register(client, login="owner") -> dict[str, str]:
    res = client.post(
        f"{API}/auth/register",
        json={"login": login, "email": f"{login}@example.com", "password": "secret123"},
    )
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def add_card(title: str, status: str = MODERATION_APPROVED) -> int:
    async def _add():
        async for session in app.dependency_overrides[get_session]():
            item = CatalogItem(type="movie", title=title, moderation_status=status)
            session.add(item)
            await session.commit()
            await session.refresh(item)
            return item.id

    return asyncio.run(_add())


def make_list(client, headers, **extra) -> int:
    res = client.post(f"{API}/me/lists", json={"title": "Вечер", **extra}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def fill(client, headers, list_id, titles) -> list[int]:
    ids = [add_card(t) for t in titles]
    for item_id in ids:
        res = client.post(
            f"{API}/me/lists/{list_id}/items", json={"item_id": item_id}, headers=headers
        )
        assert res.status_code == 201, res.text
    return ids


def test_guest_cannot_use_my_lists(client):
    assert client.get(f"{API}/me/lists").status_code == 401
    assert client.post(f"{API}/me/lists", json={"title": "x"}).status_code == 401


def test_create_update_delete(client):
    h = register(client)
    list_id = make_list(client, h)

    res = client.patch(
        f"{API}/me/lists/{list_id}",
        json={"title": "Новое имя", "theme": "noir", "is_public": True},
        headers=h,
    )
    assert res.status_code == 200
    body = res.json()
    assert (body["title"], body["theme"], body["is_public"]) == ("Новое имя", "noir", True)
    assert [x["id"] for x in client.get(f"{API}/me/lists", headers=h).json()] == [list_id]

    assert client.delete(f"{API}/me/lists/{list_id}", headers=h).status_code == 204
    assert client.get(f"{API}/me/lists/{list_id}", headers=h).status_code == 404


def test_unknown_theme_and_empty_title_rejected(client):
    h = register(client)
    assert (
        client.post(f"{API}/me/lists", json={"title": "x", "theme": "neon"}, headers=h).status_code
        == 422
    )
    assert client.post(f"{API}/me/lists", json={"title": "   "}, headers=h).status_code == 422


def test_order_is_saved(client):
    h = register(client)
    list_id = make_list(client, h)
    ids = fill(client, h, list_id, ("А", "Б", "В"))

    new_order = [ids[2], ids[0], ids[1]]
    res = client.put(f"{API}/me/lists/{list_id}/order", json={"item_ids": new_order}, headers=h)
    assert res.status_code == 200

    # «после перезагрузки» читаем заново
    loaded = client.get(f"{API}/me/lists/{list_id}", headers=h).json()
    assert [row["item"]["id"] for row in loaded["items"]] == new_order


def test_order_must_match_items(client):
    h = register(client)
    list_id = make_list(client, h)
    a, b = fill(client, h, list_id, ("А", "Б"))

    for bad in ([a], [a, a], [a, b, 999]):
        res = client.put(f"{API}/me/lists/{list_id}/order", json={"item_ids": bad}, headers=h)
        assert res.status_code == 422


def test_note_limit_500(client):
    h = register(client)
    list_id = make_list(client, h)
    item_id = add_card("А")

    too_long = "я" * 501
    res = client.post(
        f"{API}/me/lists/{list_id}/items", json={"item_id": item_id, "note": too_long}, headers=h
    )
    assert res.status_code == 422

    ok = client.post(
        f"{API}/me/lists/{list_id}/items", json={"item_id": item_id, "note": "я" * 500}, headers=h
    )
    assert ok.status_code == 201

    res = client.patch(
        f"{API}/me/lists/{list_id}/items/{item_id}", json={"note": too_long}, headers=h
    )
    assert res.status_code == 422

    res = client.patch(
        f"{API}/me/lists/{list_id}/items/{item_id}", json={"note": "  коротко  "}, headers=h
    )
    assert res.json()["items"][0]["note"] == "коротко"


def test_duplicate_and_missing_item(client):
    h = register(client)
    list_id = make_list(client, h)
    (item_id,) = fill(client, h, list_id, ("А",))

    dup = client.post(f"{API}/me/lists/{list_id}/items", json={"item_id": item_id}, headers=h)
    assert dup.status_code == 409
    missing = client.post(f"{API}/me/lists/{list_id}/items", json={"item_id": 9999}, headers=h)
    assert missing.status_code == 404


def test_remove_item_renumbers(client):
    h = register(client)
    list_id = make_list(client, h)
    ids = fill(client, h, list_id, ("А", "Б", "В"))

    res = client.delete(f"{API}/me/lists/{list_id}/items/{ids[0]}", headers=h)
    assert res.status_code == 200
    assert [r["position"] for r in res.json()["items"]] == [0, 1]
    assert [r["item"]["id"] for r in res.json()["items"]] == [ids[1], ids[2]]


def test_private_list_is_404_on_public_route(client):
    h = register(client)
    private_id = make_list(client, h)
    public_id = make_list(client, h, is_public=True, theme="pastel")
    item_id = add_card("Манас")
    client.post(
        f"{API}/me/lists/{public_id}/items", json={"item_id": item_id, "note": "Эпос"}, headers=h
    )

    assert client.get(f"{API}/public/lists/{private_id}").status_code == 404
    assert client.get(f"{API}/public/lists/9999").status_code == 404

    res = client.get(f"{API}/public/lists/{public_id}")  # без токена
    assert res.status_code == 200
    body = res.json()
    assert body["theme"] == "pastel"
    assert body["owner"]["login"] == "owner"
    assert body["items"][0]["note"] == "Эпос"


def test_list_becomes_404_after_unpublish(client):
    h = register(client)
    list_id = make_list(client, h, is_public=True)
    assert client.get(f"{API}/public/lists/{list_id}").status_code == 200
    client.patch(f"{API}/me/lists/{list_id}", json={"is_public": False}, headers=h)
    assert client.get(f"{API}/public/lists/{list_id}").status_code == 404


def test_foreign_list_is_404(client):
    owner = register(client, "owner")
    other = register(client, "other")
    list_id = make_list(client, owner)
    item_id = add_card("А")

    assert client.get(f"{API}/me/lists/{list_id}", headers=other).status_code == 404
    assert (
        client.patch(f"{API}/me/lists/{list_id}", json={"title": "x"}, headers=other).status_code
        == 404
    )
    assert client.delete(f"{API}/me/lists/{list_id}", headers=other).status_code == 404
    add = client.post(f"{API}/me/lists/{list_id}/items", json={"item_id": item_id}, headers=other)
    assert add.status_code == 404


def test_hidden_card_not_shown_in_showcase(client):
    h = register(client)
    list_id = make_list(client, h, is_public=True)
    visible, hidden = fill(client, h, list_id, ("Видна", "Скрыта"))

    async def _hide():
        async for session in app.dependency_overrides[get_session]():
            item = await session.get(CatalogItem, hidden)
            item.moderation_status = MODERATION_HIDDEN
            await session.commit()
            return

    asyncio.run(_hide())
    body = client.get(f"{API}/public/lists/{list_id}").json()
    assert [r["item"]["title"] for r in body["items"]] == ["Видна"]
    assert body["items_count"] == 1
    assert visible


def test_profile_lists_shows_only_public(client):
    h = register(client, "alice")
    make_list(client, h)  # приватный
    public_id = make_list(client, h, is_public=True)

    res = client.get(f"{API}/users/alice/lists")
    assert res.status_code == 200
    assert [x["id"] for x in res.json()["items"]] == [public_id]
    assert res.json()["total"] == 1


@pytest.mark.parametrize("theme", ["classic", "noir", "pastel"])
def test_all_themes_accepted(client, theme):
    h = register(client)
    res = client.post(f"{API}/me/lists", json={"title": "t", "theme": theme}, headers=h)
    assert res.status_code == 201
