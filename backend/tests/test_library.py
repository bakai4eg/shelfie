"""Тесты полок и оценок (ТЗ 4.2.2, 4.4.1, 4.4.2)."""

import asyncio

from app.core.constants import MODERATION_APPROVED, MODERATION_HIDDEN
from app.db.session import get_session
from app.main import app
from app.models.catalog import CatalogItem

API = "/api"


def register(client, login: str = "elvina") -> dict:
    res = client.post(
        f"{API}/auth/register",
        json={"login": login, "email": f"{login.lower()}@example.com", "password": "secret123"},
    )
    assert res.status_code == 201, res.text
    return res.json()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def add_card(
    title: str = "Дюна",
    mod_status: str = MODERATION_APPROVED,
    item_type: str = "book",
) -> int:
    async def _add():
        async for session in app.dependency_overrides[get_session]():
            item = CatalogItem(
                type=item_type,
                title=title,
                moderation_status=mod_status,
                is_local=False,
            )
            session.add(item)
            await session.commit()
            await session.refresh(item)
            return item.id

    return asyncio.run(_add())


def test_shelf_guest_rejected(client):
    res = client.get(f"{API}/me/library")
    assert res.status_code == 401

    res = client.put(f"{API}/me/library/1", json={"status": "watching"})
    assert res.status_code == 401

    res = client.put(f"{API}/me/ratings/1", json={"value": 8})
    assert res.status_code == 401


def test_shelf_upsert_list_and_delete(client):
    user = register(client, "reader1")
    headers = auth(user["access_token"])
    item_id = add_card("Интерстеллар", item_type="movie")

    # Добавляем на полку
    res = client.put(
        f"{API}/me/library/{item_id}",
        json={"status": "watching"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "watching"
    assert res.json()["finished_at"] is None

    # Проверяем в списке
    res = client.get(f"{API}/me/library", headers=headers)
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["item"]["title"] == "Интерстеллар"
    assert items[0]["user_rating"] is None

    # Ставим оценку
    res = client.put(f"{API}/me/ratings/{item_id}", json={"value": 9}, headers=headers)
    assert res.status_code == 200
    assert res.json()["value"] == 9
    assert res.json()["rating_avg"] == 9.0
    assert res.json()["ratings_count"] == 1

    # Теперь в списке виден user_rating
    res = client.get(f"{API}/me/library", headers=headers)
    assert res.json()[0]["user_rating"] == 9

    # Удаляем с полки
    res = client.delete(f"{API}/me/library/{item_id}", headers=headers)
    assert res.status_code == 204

    # Список пуст
    res = client.get(f"{API}/me/library", headers=headers)
    assert len(res.json()) == 0


def test_shelf_finished_at_validation(client):
    user = register(client, "reader2")
    headers = auth(user["access_token"])
    item_id = add_card("Дюна", item_type="book")

    # finished без finished_at отклоняется
    res = client.put(
        f"{API}/me/library/{item_id}",
        json={"status": "finished"},
        headers=headers,
    )
    assert res.status_code == 422

    # finished с finished_at успешен
    res = client.put(
        f"{API}/me/library/{item_id}",
        json={"status": "finished", "finished_at": "2026-10-28"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["finished_at"] == "2026-10-28"

    # смена статуса на planned затирает finished_at в null
    res = client.put(
        f"{API}/me/library/{item_id}",
        json={"status": "planned", "finished_at": "2026-10-28"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["finished_at"] is None


def test_rating_recomputation_and_delete(client):
    u1 = register(client, "critic1")
    u2 = register(client, "critic2")
    h1 = auth(u1["access_token"])
    h2 = auth(u2["access_token"])
    item_id = add_card("Гарри Поттер", item_type="book")

    # первый ставит 10
    r1 = client.put(f"{API}/me/ratings/{item_id}", json={"value": 10}, headers=h1)
    assert r1.status_code == 200
    assert r1.json()["rating_avg"] == 10.0
    assert r1.json()["ratings_count"] == 1

    # второй ставит 6
    r2 = client.put(f"{API}/me/ratings/{item_id}", json={"value": 6}, headers=h2)
    assert r2.status_code == 200
    assert r2.json()["rating_avg"] == 8.0
    assert r2.json()["ratings_count"] == 2

    # карточка в каталоге тоже обновилась
    card = client.get(f"{API}/catalog/{item_id}")
    assert card.status_code == 200
    assert card.json()["rating_avg"] == 8.0
    assert card.json()["ratings_count"] == 2

    # первый удаляет оценку
    del_res = client.delete(f"{API}/me/ratings/{item_id}", headers=h1)
    assert del_res.status_code == 204

    card = client.get(f"{API}/catalog/{item_id}")
    assert card.json()["rating_avg"] == 6.0
    assert card.json()["ratings_count"] == 1


def test_hidden_card_returns_404(client):
    user = register(client, "reader3")
    headers = auth(user["access_token"])
    hidden_id = add_card("Скрытая книга", mod_status=MODERATION_HIDDEN)

    assert client.get(f"{API}/catalog/{hidden_id}").status_code == 404
    shelf_res = client.put(
        f"{API}/me/library/{hidden_id}", json={"status": "watching"}, headers=headers
    )
    assert shelf_res.status_code == 404
    rating_res = client.put(
        f"{API}/me/ratings/{hidden_id}", json={"value": 5}, headers=headers
    )
    assert rating_res.status_code == 404


def test_shelf_filters_and_sorting_without_ratings(client):
    """Сортировка «по оценке» не падает, если оценок ещё нет (приёмка T2.4)."""
    user = register(client, "sorter")
    headers = auth(user["access_token"])
    book_id = add_card("Алла", item_type="book")
    movie_id = add_card("Берег", item_type="movie")
    series_id = add_card("Ветер", item_type="series")

    client.put(f"{API}/me/library/{book_id}", json={"status": "watching"}, headers=headers)
    client.put(
        f"{API}/me/library/{movie_id}",
        json={"status": "finished", "finished_at": "2026-10-01"},
        headers=headers,
    )
    client.put(f"{API}/me/library/{series_id}", json={"status": "planned"}, headers=headers)

    watching = client.get(f"{API}/me/library?status=watching", headers=headers)
    assert watching.status_code == 200
    assert [entry["item"]["title"] for entry in watching.json()] == ["Алла"]

    movies = client.get(f"{API}/me/library?type=movie", headers=headers)
    assert [entry["item"]["title"] for entry in movies.json()] == ["Берег"]

    by_title = client.get(f"{API}/me/library?sort=title_asc", headers=headers)
    assert [entry["item"]["title"] for entry in by_title.json()] == [
        "Алла",
        "Берег",
        "Ветер",
    ]

    by_rating = client.get(f"{API}/me/library?sort=rating_desc", headers=headers)
    assert by_rating.status_code == 200
    assert len(by_rating.json()) == 3


def test_finished_at_can_be_edited(client):
    user = register(client, "editor")
    headers = auth(user["access_token"])
    item_id = add_card("Редактируемая дата", item_type="book")

    first = client.put(
        f"{API}/me/library/{item_id}",
        json={"status": "finished", "finished_at": "2026-10-01"},
        headers=headers,
    )
    assert first.status_code == 200

    edited = client.put(
        f"{API}/me/library/{item_id}",
        json={"status": "finished", "finished_at": "2026-10-05"},
        headers=headers,
    )
    assert edited.status_code == 200
    assert edited.json()["finished_at"] == "2026-10-05"

    # PUT идемпотентен: запись на полке одна.
    entries = client.get(f"{API}/me/library", headers=headers).json()
    assert len(entries) == 1


def test_remove_absent_shelf_entry_returns_404(client):
    user = register(client, "remover")
    headers = auth(user["access_token"])
    item_id = add_card("Не на полке", item_type="book")

    missing = client.delete(f"{API}/me/library/{item_id}", headers=headers)
    assert missing.status_code == 404
