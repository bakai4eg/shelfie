"""Публичный профиль и его разделы (T1.3)."""


def register(client, login: str = "elvina") -> dict:
    response = client.post(
        "/api/auth/register",
        json={"login": login, "email": f"{login.lower()}@example.com", "password": "secret123"},
    )
    assert response.status_code == 201, response.text
    return response.json()


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
