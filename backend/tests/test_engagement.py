"""T4.4, T5.3, T5.4: комментарии, лайки, подписки и лента активности."""

import asyncio

from sqlalchemy import func, select

from app.core.constants import MODERATION_APPROVED, ROLE_ADMIN, ROLE_MODERATOR
from app.db.session import get_session
from app.main import app
from app.models.audit import AuditLog
from app.models.catalog import CatalogItem
from app.models.moderation import Report
from app.models.social import ActivityEvent, Comment, Like, Review
from app.models.user import User

API = "/api"


def register(client, login):
    res = client.post(
        f"{API}/auth/register",
        json={"login": login, "email": f"{login}@example.com", "password": "secret123"},
    )
    assert res.status_code == 201, res.text
    return res.json()["user"]["id"], {"Authorization": f"Bearer {res.json()['access_token']}"}


def db_run(coro_fn):
    async def _go():
        async for session in app.dependency_overrides[get_session]():
            return await coro_fn(session)

    return asyncio.run(_go())


def give_role(user_id, role):
    async def _set(s):
        (await s.get(User, user_id)).role = role
        await s.commit()

    db_run(_set)


def count(model, *where):
    async def _count(s):
        return await s.scalar(select(func.count()).select_from(model).where(*where))

    return db_run(_count)


def add_card(title="Фильм"):
    async def _add(s):
        item = CatalogItem(
            type="movie",
            title=title,
            moderation_status=MODERATION_APPROVED,
            source="tmdb",
            external_id=title,
        )
        s.add(item)
        await s.commit()
        await s.refresh(item)
        return item.id

    return db_run(_add)


def write_review(client, headers, item_id, title="Рецензия"):
    res = client.post(
        f"{API}/catalog/{item_id}/reviews",
        json={"title": title, "body": "Текст рецензии", "rating": 7},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def comment(client, headers, review_id, body="Согласен"):
    res = client.post(f"{API}/reviews/{review_id}/comments", json={"body": body}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def like(client, headers, target_type, target_id):
    return client.post(
        f"{API}/likes", json={"target_type": target_type, "target_id": target_id}, headers=headers
    )


def unlike(client, headers, target_type, target_id):
    return client.request(
        "DELETE",
        f"{API}/likes",
        json={"target_type": target_type, "target_id": target_id},
        headers=headers,
    )


# --- T4.4 комментарии ---


def test_comment_create_list_and_counter(client):
    _, author = register(client, "author")
    _, reader = register(client, "reader")
    review_id = write_review(client, author, add_card())

    assert client.post(f"{API}/reviews/{review_id}/comments", json={"body": "x"}).status_code == 401
    comment(client, reader, review_id, "Первый")
    comment(client, author, review_id, "Второй")

    listing = client.get(f"{API}/reviews/{review_id}/comments").json()  # гость читает
    assert [c["body"] for c in listing["items"]] == ["Первый", "Второй"]
    assert listing["total"] == 2
    assert listing["items"][0]["user_login"] == "reader"

    assert client.get(f"{API}/reviews/{review_id}").json()["comments_count"] == 2


def test_comment_validation_and_pagination(client):
    _, author = register(client, "author")
    review_id = write_review(client, author, add_card())
    url = f"{API}/reviews/{review_id}/comments"

    assert client.post(url, json={"body": "я" * 1001}, headers=author).status_code == 422
    assert client.post(url, json={"body": "   "}, headers=author).status_code == 422
    assert client.post(url, json={"body": "я" * 1000}, headers=author).status_code == 201
    assert (
        client.post(f"{API}/reviews/9999/comments", json={"body": "x"}, headers=author).status_code
        == 404
    )

    for n in range(4):
        comment(client, author, review_id, f"c{n}")
    page = client.get(f"{url}?size=2&page=2").json()
    assert len(page["items"]) == 2 and page["total"] == 5


def test_comment_delete_rights(client):
    _, author = register(client, "author")
    _, other = register(client, "other")
    mod_id, mod = register(client, "mod")
    give_role(mod_id, ROLE_MODERATOR)
    review_id = write_review(client, author, add_card())
    mine = comment(client, other, review_id)
    theirs = comment(client, author, review_id)

    assert client.delete(f"{API}/comments/{theirs}", headers=other).status_code == 403
    assert client.delete(f"{API}/comments/{theirs}").status_code == 401
    assert client.delete(f"{API}/comments/{mine}", headers=other).status_code == 204
    assert client.delete(f"{API}/comments/{theirs}", headers=mod).status_code == 204
    assert count(AuditLog, AuditLog.target_type == "comment") == 1  # удаление модератором в журнале
    assert client.delete(f"{API}/comments/{theirs}", headers=mod).status_code == 404


def test_hidden_review_hides_its_comments(client):
    _, author = register(client, "author")
    mod_id, mod = register(client, "mod")
    give_role(mod_id, ROLE_MODERATOR)
    review_id = write_review(client, author, add_card())
    comment(client, author, review_id)

    client.post(
        f"{API}/moderation/content/review/{review_id}/hide", json={"reason": "спам"}, headers=mod
    )
    assert client.get(f"{API}/reviews/{review_id}/comments").status_code == 404  # гость
    assert client.get(f"{API}/reviews/{review_id}").status_code == 404
    assert client.get(f"{API}/reviews/{review_id}/comments", headers=author).json()["items"] == []
    assert (
        client.post(
            f"{API}/reviews/{review_id}/comments", json={"body": "x"}, headers=author
        ).status_code
        == 404
    )


def test_report_and_moderate_comment(client):
    _, author = register(client, "author")
    _, rep = register(client, "reporter")
    mod_id, mod = register(client, "mod")
    give_role(mod_id, ROLE_MODERATOR)
    review_id = write_review(client, author, add_card())
    comment_id = comment(client, author, review_id, "Грубость")

    own = client.post(
        f"{API}/reports",
        json={"target_type": "comment", "target_id": comment_id, "reason": "insult"},
        headers=author,
    )
    assert own.status_code == 409  # на свой комментарий нельзя
    sent = client.post(
        f"{API}/reports",
        json={"target_type": "comment", "target_id": comment_id, "reason": "insult"},
        headers=rep,
    )
    assert sent.status_code == 201 and sent.json()["target_title"] == "Грубость"

    res = client.post(
        f"{API}/moderation/reports/{sent.json()['id']}/resolve",
        json={"decision": "hide", "reason": "оскорбление"},
        headers=mod,
    )
    assert res.status_code == 200
    assert client.get(f"{API}/reviews/{review_id}/comments").json()["items"] == []
    assert count(Comment, Comment.id == comment_id) == 1  # скрыт, но в БД


# --- T5.3 лайки ---


def test_likes_on_review_and_comment_are_idempotent(client):
    _, author = register(client, "author")
    _, fan = register(client, "fan")
    review_id = write_review(client, author, add_card())
    comment_id = comment(client, author, review_id)

    assert (
        client.post(
            f"{API}/likes", json={"target_type": "review", "target_id": review_id}
        ).status_code
        == 401
    )

    first = like(client, fan, "review", review_id).json()
    assert (first["likes_count"], first["liked_by_me"]) == (1, True)
    again = like(client, fan, "review", review_id).json()
    assert again["likes_count"] == 1  # повторный лайк не растит счётчик
    assert like(client, author, "review", review_id).json()["likes_count"] == 2

    assert like(client, fan, "comment", comment_id).json()["likes_count"] == 1

    mine = client.get(f"{API}/reviews/{review_id}", headers=fan).json()
    guest = client.get(f"{API}/reviews/{review_id}").json()
    assert (mine["likes_count"], mine["liked_by_me"]) == (2, True)
    assert (guest["likes_count"], guest["liked_by_me"]) == (2, False)
    comments = client.get(f"{API}/reviews/{review_id}/comments", headers=fan).json()["items"]
    assert (comments[0]["likes_count"], comments[0]["liked_by_me"]) == (1, True)

    off = unlike(client, fan, "review", review_id).json()
    assert (off["likes_count"], off["liked_by_me"]) == (1, False)
    assert (
        unlike(client, fan, "review", review_id).json()["likes_count"] == 1
    )  # снятие тоже идемпотентно


def test_like_validation(client):
    _, fan = register(client, "fan")
    assert like(client, fan, "review", 9999).status_code == 404
    assert like(client, fan, "comment", 9999).status_code == 404
    assert like(client, fan, "card", 1).status_code == 422


def test_hidden_material_cannot_be_liked(client):
    _, author = register(client, "author")
    _, fan = register(client, "fan")
    mod_id, mod = register(client, "mod")
    give_role(mod_id, ROLE_MODERATOR)
    review_id = write_review(client, author, add_card())
    comment_id = comment(client, author, review_id)

    client.post(
        f"{API}/moderation/content/review/{review_id}/hide", json={"reason": "r"}, headers=mod
    )
    assert like(client, fan, "review", review_id).status_code == 404
    assert (
        like(client, fan, "comment", comment_id).status_code == 404
    )  # комментарий скрытой рецензии


def test_deleting_review_removes_comments_likes_reports_and_events(client):
    _, author = register(client, "author")
    _, fan = register(client, "fan")
    mod_id, mod = register(client, "mod")
    give_role(mod_id, ROLE_MODERATOR)
    review_id = write_review(client, author, add_card())
    comment_id = comment(client, fan, review_id)
    like(client, fan, "review", review_id)
    like(client, author, "comment", comment_id)
    client.post(
        f"{API}/reports",
        json={"target_type": "comment", "target_id": comment_id, "reason": "spam"},
        headers=author,
    )
    assert count(ActivityEvent, ActivityEvent.review_id == review_id) == 1

    res = client.post(
        f"{API}/moderation/content/review/{review_id}/delete",
        json={"reason": "нарушение"},
        headers=mod,
    )
    assert res.status_code == 204
    assert count(Review) == 0
    assert count(Comment) == 0
    assert count(Like) == 0
    assert count(Report) == 0
    assert count(ActivityEvent, ActivityEvent.review_id == review_id) == 0


def test_author_delete_review_cascades_too(client):
    _, author = register(client, "author")
    _, fan = register(client, "fan")
    review_id = write_review(client, author, add_card())
    comment(client, fan, review_id)
    like(client, fan, "review", review_id)

    assert client.delete(f"{API}/reviews/{review_id}", headers=author).status_code == 204
    assert (count(Comment), count(Like)) == (0, 0)


# --- T5.4 подписки и лента ---


def follow(client, headers, login):
    return client.post(f"{API}/users/{login}/follow", headers=headers)


def feed(client, headers, **params):
    query = "&".join(f"{k}={v}" for k, v in params.items())
    res = client.get(f"{API}/feed?{query}", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


def test_feed_requires_login_and_starts_empty(client):
    _, me = register(client, "viewer")
    assert client.get(f"{API}/feed").status_code == 401
    assert feed(client, me) == {"items": [], "total": 0, "page": 1, "size": 20}


def test_follow_unfollow_counters(client):
    _, me = register(client, "viewer")
    register(client, "star")
    state = follow(client, me, "star").json()
    assert (state["is_following"], state["followers"]) == (True, 1)
    assert follow(client, me, "viewer").status_code == 400  # на себя нельзя
    assert client.get(f"{API}/users/star/followers").json()[0]["login"] == "viewer"
    assert client.get(f"{API}/users/viewer/following").json()[0]["login"] == "star"
    gone = client.delete(f"{API}/users/star/follow", headers=me).json()
    assert (gone["is_following"], gone["followers"]) == (False, 0)


def test_feed_shows_all_event_types_newest_first(client):
    _, me = register(client, "viewer")
    _, star = register(client, "star")
    follow(client, me, "star")
    item = add_card("Матрица")

    client.put(
        f"{API}/me/library/{item}",
        json={"status": "finished", "finished_at": "2026-11-01"},
        headers=star,
    )
    client.put(f"{API}/me/ratings/{item}", json={"value": 9}, headers=star)
    write_review(client, star, item, "Мой взгляд")
    client.post(f"{API}/me/lists", json={"title": "Топ", "is_public": True}, headers=star)

    events = feed(client, me)["items"]
    assert [e["event_type"] for e in events] == [
        "list_published",
        "review_created",
        "rating_set",
        "item_finished",
    ]
    assert events[0]["list"]["title"] == "Топ"
    assert events[1]["review"]["title"] == "Мой взгляд" and events[1]["item"]["title"] == "Матрица"
    assert events[2]["value"] == 9
    assert events[3]["item"]["title"] == "Матрица" and events[3]["user"]["login"] == "star"


def test_feed_events_are_not_duplicated(client):
    _, me = register(client, "viewer")
    _, star = register(client, "star")
    follow(client, me, "star")
    item = add_card()
    for _ in range(3):
        client.put(f"{API}/me/ratings/{item}", json={"value": 8}, headers=star)
        client.put(
            f"{API}/me/library/{item}",
            json={"status": "finished", "finished_at": "2026-11-01"},
            headers=star,
        )
    list_id = client.post(
        f"{API}/me/lists", json={"title": "L", "is_public": True}, headers=star
    ).json()["id"]
    client.patch(f"{API}/me/lists/{list_id}", json={"is_public": False}, headers=star)
    client.patch(f"{API}/me/lists/{list_id}", json={"is_public": True}, headers=star)

    types = sorted(e["event_type"] for e in feed(client, me)["items"])
    assert types == ["item_finished", "list_published", "rating_set"]


def test_feed_only_followed_and_unfollow_removes_events(client):
    _, me = register(client, "viewer")
    _, star = register(client, "star")
    _, stranger = register(client, "stranger")
    item = add_card()
    write_review(client, stranger, item)
    write_review(client, star, item)
    follow(client, me, "star")

    assert [e["user"]["login"] for e in feed(client, me)["items"]] == ["star"]
    client.delete(f"{API}/users/star/follow", headers=me)
    assert feed(client, me)["items"] == []


def test_feed_hides_hidden_reviews_and_private_lists(client):
    _, me = register(client, "viewer")
    _, star = register(client, "star")
    mod_id, mod = register(client, "mod")
    give_role(mod_id, ROLE_MODERATOR)
    follow(client, me, "star")
    item = add_card()
    review_id = write_review(client, star, item)
    list_id = client.post(
        f"{API}/me/lists", json={"title": "L", "is_public": True}, headers=star
    ).json()["id"]
    assert len(feed(client, me)["items"]) == 2

    client.post(
        f"{API}/moderation/content/review/{review_id}/hide", json={"reason": "спам"}, headers=mod
    )
    client.patch(f"{API}/me/lists/{list_id}", json={"is_public": False}, headers=star)
    assert feed(client, me)["items"] == []


def test_feed_pagination(client):
    _, me = register(client, "viewer")
    _, star = register(client, "star")
    follow(client, me, "star")
    for n in range(5):
        client.put(f"{API}/me/ratings/{add_card(f'К{n}')}", json={"value": 5}, headers=star)

    first = feed(client, me, size=2, page=1)
    last = feed(client, me, size=2, page=3)
    assert (first["total"], len(first["items"]), len(last["items"])) == (5, 2, 1)
    ids = [e["id"] for e in feed(client, me, size=50)["items"]]
    assert ids == sorted(ids, reverse=True)


def test_deleting_user_removes_comments_likes_and_events(client):
    boss_id, boss = register(client, "boss")
    give_role(boss_id, ROLE_ADMIN)
    victim_id, victim = register(client, "victim")
    _, other = register(client, "other")
    review_id = write_review(client, other, add_card())
    comment(client, victim, review_id)
    like(client, victim, "review", review_id)
    client.put(f"{API}/me/ratings/{add_card('Второй')}", json={"value": 6}, headers=victim)

    assert client.delete(f"{API}/admin/users/{victim_id}", headers=boss).status_code == 204
    assert (count(Comment), count(Like)) == (0, 0)
    assert count(ActivityEvent, ActivityEvent.user_id == victim_id) == 0
    assert client.get(f"{API}/reviews/{review_id}").json()["comments_count"] == 0
