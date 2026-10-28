"""Публичный профиль и его разделы (T1.3, ТЗ 4.2.3)."""

import asyncio

from app.core.constants import MODERATION_APPROVED
from app.db.session import get_session
from app.main import app
from app.models.catalog import CatalogItem


def register(client, login: str = "elvina") -> dict:
    response = client.post(
        "/api/auth/register",
        json={"login": login, "email": f"{login.lower()}@example.com", "password": "secret123"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def add_item(title: str, item_type: str) -> int:
    async def _add():
        async for session in app.dependency_overrides[get_session]():
            item = CatalogItem(
                type=item_type,
                title=title,
                moderation_status=MODERATION_APPROVED,
                is_local=False,
            )
            session.add(item)
            await session.commit()
            await session.refresh(item)
            return item.id

    return asyncio.run(_add())


def test_public_profile_is_open_to_guest(client):
    created = register(client)
    login = created["user"]["login"]

    response = client.get(f"/api/users/{login}")

    assert response.status_code == 200
    body = response.json()
    assert body["login"] == login
    assert body["bio"] is None
    assert body["avatar_url"] is None
    assert body["is_following"] is False
    assert body["registered_at"]
    assert body["stats"] == {
        "books_read": 0,
        "movies_watched": 0,
        "series_watched": 0,
        "ratings_count": 0,
        "rating_avg": 0,
        "reviews_count": 0,
        "followers": 0,
        "following": 0,
    }


def test_login_lookup_is_case_insensitive(client):
    register(client, login="Bakai")

    assert client.get("/api/users/bakai").status_code == 200
    assert client.get("/api/users/BAKAI").status_code == 200


def test_unknown_profile_returns_404(client):
    response = client.get("/api/users/nobody")

    assert response.status_code == 404
    assert response.json()["detail"] == "Пользователь не найден"


def test_profile_does_not_leak_email_or_password(client):
    register(client, login="closed")

    body = client.get("/api/users/closed").json()

    assert "email" not in body
    assert "password_hash" not in body
    assert "role" not in body


def test_reviews_and_lists_are_empty_pages(client):
    register(client, login="reader")

    reviews = client.get("/api/users/reader/reviews")
    lists = client.get("/api/users/reader/lists")

    assert reviews.status_code == 200
    assert reviews.json() == {"items": [], "total": 0, "page": 1, "size": 20}
    assert lists.status_code == 200
    assert lists.json() == {"items": [], "total": 0, "page": 1, "size": 20}


def test_sections_of_unknown_user_return_404(client):
    assert client.get("/api/users/nobody/reviews").status_code == 404
    assert client.get("/api/users/nobody/lists").status_code == 404


def test_section_pagination_is_validated(client):
    register(client, login="reader")

    assert client.get("/api/users/reader/reviews", params={"page": 0}).status_code == 422
    assert client.get("/api/users/reader/lists", params={"size": 101}).status_code == 422


def test_profile_stats_update_dynamically(client):
    u = register(client, "active_user")
    other = register(client, "other_user")
    h = auth(u["access_token"])
    h_other = auth(other["access_token"])

    book_id = add_item("Книга 1", "book")
    movie_id = add_item("Фильм 1", "movie")
    series_id = add_item("Сериал 1", "series")

    # 1. Полка: сначала watching (не finished)
    client.put(f"/api/me/library/{book_id}", json={"status": "watching"}, headers=h)
    stats = client.get("/api/users/active_user").json()["stats"]
    assert stats["books_read"] == 0

    # переводим в finished
    client.put(
        f"/api/me/library/{book_id}",
        json={"status": "finished", "finished_at": "2026-10-28"},
        headers=h,
    )
    # добавляем фильм и сериал в finished
    client.put(
        f"/api/me/library/{movie_id}",
        json={"status": "finished", "finished_at": "2026-10-28"},
        headers=h,
    )
    client.put(
        f"/api/me/library/{series_id}",
        json={"status": "finished", "finished_at": "2026-10-28"},
        headers=h,
    )

    stats = client.get("/api/users/active_user").json()["stats"]
    assert stats["books_read"] == 1
    assert stats["movies_watched"] == 1
    assert stats["series_watched"] == 1

    # 2. Оценки
    client.put(f"/api/me/ratings/{book_id}", json={"value": 8}, headers=h)
    client.put(f"/api/me/ratings/{movie_id}", json={"value": 10}, headers=h)

    stats = client.get("/api/users/active_user").json()["stats"]
    assert stats["ratings_count"] == 2
    assert stats["rating_avg"] == 9.0

    # 3. Рецензия
    client.post(
        f"/api/catalog/{movie_id}/reviews",
        json={"title": "Отличный фильм", "body": "Очень понравился сюжет", "rating": 10},
        headers=h,
    )
    stats = client.get("/api/users/active_user").json()["stats"]
    assert stats["reviews_count"] == 1

    # Рецензия видна в /users/{login}/reviews
    user_revs = client.get("/api/users/active_user/reviews").json()
    assert user_revs["total"] == 1
    assert user_revs["items"][0]["title"] == "Отличный фильм"

    # 4. Подписчики и подписки
    # other_user подписывается на active_user
    client.post("/api/users/active_user/follow", headers=h_other)
    # active_user подписывается на other_user
    client.post("/api/users/other_user/follow", headers=h)

    stats = client.get("/api/users/active_user").json()["stats"]
    assert stats["followers"] == 1
    assert stats["following"] == 1
