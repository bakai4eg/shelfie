"""Тесты рецензий (ТЗ 4.2.2, 4.5.1)."""

import asyncio

from app.core.constants import MODERATION_APPROVED
from app.db.session import get_session
from app.main import app
from app.models.catalog import CatalogItem

API = "/api"


def register(client, login: str = "writer") -> dict:
    res = client.post(
        f"{API}/auth/register",
        json={"login": login, "email": f"{login.lower()}@example.com", "password": "secret123"},
    )
    assert res.status_code == 201, res.text
    return res.json()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def add_card(title: str = "Матрица") -> int:
    async def _add():
        async for session in app.dependency_overrides[get_session]():
            item = CatalogItem(
                type="movie",
                title=title,
                moderation_status=MODERATION_APPROVED,
                is_local=False,
            )
            session.add(item)
            await session.commit()
            await session.refresh(item)
            return item.id

    return asyncio.run(_add())


def test_review_create_and_conflict(client):
    u = register(client, "writer1")
    h = auth(u["access_token"])
    item_id = add_card("Матрица")

    # гость не может написать
    guest_res = client.post(
        f"{API}/catalog/{item_id}/reviews", json={"title": "Круто", "body": "Текст"}
    )
    assert guest_res.status_code == 401

    # автор пишет рецензию
    res = client.post(
        f"{API}/catalog/{item_id}/reviews",
        json={"title": "Шедевр кино", "body": "Культовый фильм девяностых", "rating": 10},
        headers=h,
    )
    assert res.status_code == 201, res.text
    assert res.json()["user_login"] == "writer1"
    assert res.json()["rating"] == 10

    # повторная рецензия на ту же карточку даёт 409
    res2 = client.post(
        f"{API}/catalog/{item_id}/reviews",
        json={"title": "Ещё раз", "body": "Второй раз"},
        headers=h,
    )
    assert res2.status_code == 409


def test_review_public_list(client):
    u = register(client, "writer2")
    h = auth(u["access_token"])
    item_id = add_card("Бойцовский клуб")

    client.post(
        f"{API}/catalog/{item_id}/reviews",
        json={"title": "Первое правило", "body": "Никому не говорить о клубе", "rating": 9},
        headers=h,
    )

    # публичный список на карточке доступен гостю
    res = client.get(f"{API}/catalog/{item_id}/reviews")
    assert res.status_code == 200
    assert res.json()["total"] == 1
    assert res.json()["items"][0]["title"] == "Первое правило"


def test_review_author_edit_and_delete(client):
    u1 = register(client, "writer3")
    u2 = register(client, "stranger")
    h1 = auth(u1["access_token"])
    h2 = auth(u2["access_token"])
    item_id = add_card("Престиж")

    res = client.post(
        f"{API}/catalog/{item_id}/reviews",
        json={"title": "Начало фокуса", "body": "Текст рецензии", "rating": 8},
        headers=h1,
    )
    rev_id = res.json()["id"]

    # чужой пользователь не может править
    res_stranger = client.patch(
        f"{API}/reviews/{rev_id}",
        json={"title": "Попытка взлома"},
        headers=h2,
    )
    assert res_stranger.status_code == 403

    # чужой не может удалить
    assert client.delete(f"{API}/reviews/{rev_id}", headers=h2).status_code == 403

    # автор правит
    res_edit = client.patch(
        f"{API}/reviews/{rev_id}",
        json={"title": "Иллюзия удалась", "rating": 9},
        headers=h1,
    )
    assert res_edit.status_code == 200
    assert res_edit.json()["title"] == "Иллюзия удалась"
    assert res_edit.json()["rating"] == 9

    # автор удаляет
    assert client.delete(f"{API}/reviews/{rev_id}", headers=h1).status_code == 204

    # в списке больше нет
    res_list = client.get(f"{API}/catalog/{item_id}/reviews")
    assert res_list.json()["total"] == 0
