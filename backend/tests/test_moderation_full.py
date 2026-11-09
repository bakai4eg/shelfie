"""T4.1 и T4.2: жалобы, скрытие и удаление материалов, очередь карточек, журнал."""

import asyncio

from sqlalchemy import func, select

from app.core.constants import (
    MODERATION_APPROVED,
    MODERATION_HIDDEN,
    MODERATION_PENDING,
    ROLE_MODERATOR,
)
from app.db.session import get_session
from app.main import app
from app.models.audit import AuditLog
from app.models.catalog import CatalogItem
from app.models.library import Rating, ShelfEntry
from app.models.lists import ListItem
from app.models.moderation import Report
from app.models.social import Review
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


def make_moderator(client, login="mod"):
    user_id, headers = register(client, login)

    async def _set(s):
        (await s.get(User, user_id)).role = ROLE_MODERATOR
        await s.commit()

    db_run(_set)
    return headers


def add_card(title="Фильм", status=MODERATION_APPROVED, local=False, creator=None):
    async def _add(s):
        item = CatalogItem(
            type="movie",
            title=title,
            moderation_status=status,
            is_local=local,
            source="local" if local else "tmdb",
            external_id=None if local else title,
            created_by=creator,
        )
        s.add(item)
        await s.commit()
        await s.refresh(item)
        return item.id

    return db_run(_add)


def count(model, *where):
    async def _count(s):
        return await s.scalar(select(func.count()).select_from(model).where(*where))

    return db_run(_count)


def write_review(client, headers, item_id, title="Рецензия"):
    res = client.post(
        f"{API}/catalog/{item_id}/reviews",
        json={"title": title, "body": "Текст рецензии", "rating": 5},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def report(client, headers, target_type, target_id, reason="spam", comment=None):
    return client.post(
        f"{API}/reports",
        json={
            "target_type": target_type,
            "target_id": target_id,
            "reason": reason,
            "comment": comment,
        },
        headers=headers,
    )


# --- T4.1 ---


def test_report_validation(client):
    _, author = register(client, "author")
    _, other = register(client, "other")
    item_id = add_card()
    review_id = write_review(client, author, item_id)

    assert (
        client.post(
            f"{API}/reports", json={"target_type": "review", "target_id": review_id}
        ).status_code
        == 401
    )
    assert report(client, other, "review", 9999).status_code == 404
    assert report(client, other, "card", 9999).status_code == 404
    assert report(client, other, "profile", 9999).status_code == 404
    # неизвестная причина
    assert report(client, other, "review", review_id, reason="boring").status_code == 422
    # «иное» без пояснения
    assert report(client, other, "review", review_id, reason="other").status_code == 422
    ok = report(client, other, "review", review_id, reason="other", comment="Очень странный текст")
    assert ok.status_code == 201
    assert ok.json()["target_author"] == "author"
    assert report(client, other, "review", review_id).status_code == 409  # повтор


def test_cannot_report_yourself(client):
    author_id, author = register(client, "author")
    item_id = add_card()
    review_id = write_review(client, author, item_id)

    own_review = report(client, author, "review", review_id)
    own_profile = report(client, author, "profile", author_id)
    assert own_review.status_code == 409
    assert own_profile.status_code == 409


def test_report_on_local_card_and_profile_reach_queue(client):
    author_id, _ = register(client, "author")
    _, reporter = register(client, "reporter")
    mod = make_moderator(client)
    card_id = add_card("Манас", status=MODERATION_PENDING, local=True, creator=author_id)

    assert report(client, reporter, "card", card_id).status_code == 201
    assert report(client, reporter, "profile", author_id, reason="insult").status_code == 201

    queue = client.get(f"{API}/moderation/reports?status=open", headers=mod).json()
    assert {(r["target_type"], r["target_title"]) for r in queue} == {
        ("card", "Манас"),
        ("profile", "Профиль @author"),
    }


# --- T4.2 ---


def test_hidden_review_disappears_but_stays_in_db(client):
    author_id, author = register(client, "author")
    _, reporter = register(client, "reporter")
    mod = make_moderator(client)
    item_id = add_card()
    review_id = write_review(client, author, item_id)
    report_id = report(client, reporter, "review", review_id).json()["id"]

    res = client.post(
        f"{API}/moderation/reports/{report_id}/resolve",
        json={"decision": "hide", "reason": "Спам"},
        headers=mod,
    )
    assert res.status_code == 200 and res.json()["status"] == "resolved"

    assert client.get(f"{API}/catalog/{item_id}/reviews").json()["total"] == 0  # из карточки
    assert client.get("/api/users/author/reviews").json()["total"] == 0  # из профиля

    async def _review(s):
        return (await s.get(Review, review_id)).is_hidden

    assert db_run(_review) is True  # но в БД осталась


def test_hide_requires_reason_and_second_resolve_conflicts(client):
    _, author = register(client, "author")
    _, reporter = register(client, "reporter")
    mod = make_moderator(client)
    review_id = write_review(client, author, add_card())
    report_id = report(client, reporter, "review", review_id).json()["id"]
    url = f"{API}/moderation/reports/{report_id}/resolve"

    assert client.post(url, json={"decision": "hide"}, headers=mod).status_code == 422
    assert client.post(url, json={"decision": "reject"}, headers=mod).status_code == 200
    assert client.post(url, json={"decision": "reject"}, headers=mod).status_code == 409


def test_hiding_closes_other_open_reports_on_same_target(client):
    _, author = register(client, "author")
    _, r1 = register(client, "rep_one")
    _, r2 = register(client, "rep_two")
    mod = make_moderator(client)
    review_id = write_review(client, author, add_card())
    first = report(client, r1, "review", review_id).json()["id"]
    report(client, r2, "review", review_id)

    client.post(
        f"{API}/moderation/reports/{first}/resolve",
        json={"decision": "hide", "reason": "Спам"},
        headers=mod,
    )
    assert client.get(f"{API}/moderation/reports?status=open", headers=mod).json() == []


def test_delete_review_removes_related_reports(client):
    _, author = register(client, "author")
    _, reporter = register(client, "reporter")
    mod = make_moderator(client)
    item_id = add_card()
    review_id = write_review(client, author, item_id)
    report_id = report(client, reporter, "review", review_id).json()["id"]

    res = client.post(
        f"{API}/moderation/reports/{report_id}/resolve",
        json={"decision": "delete", "reason": "Оскорбления"},
        headers=mod,
    )
    assert res.status_code == 200
    assert res.json()["resolution"] == "delete"

    assert count(Review, Review.id == review_id) == 0
    assert count(Report, Report.target_type == "review") == 0
    # решение осталось в журнале
    assert count(AuditLog, AuditLog.action == "report.resolve") == 1
    assert count(AuditLog, AuditLog.action == "content.delete") == 1


def test_delete_card_cascades(client):
    author_id, _ = register(client, "author")
    reader_id, reader = register(client, "reader")
    _, reporter = register(client, "reporter")
    mod = make_moderator(client)
    card_id = add_card("Кыргыз", status=MODERATION_APPROVED, local=True, creator=author_id)
    other_card = add_card("Другая")

    review_id = write_review(client, reader, card_id)
    client.put(f"{API}/me/ratings/{card_id}", json={"value": 8}, headers=reader)
    client.put(f"{API}/me/library/{card_id}", json={"status": "planned"}, headers=reader)
    list_id = client.post(f"{API}/me/lists", json={"title": "L"}, headers=reader).json()["id"]
    client.post(f"{API}/me/lists/{list_id}/items", json={"item_id": card_id}, headers=reader)
    client.post(f"{API}/me/lists/{list_id}/items", json={"item_id": other_card}, headers=reader)
    report(client, reporter, "card", card_id)
    report(client, reporter, "review", review_id, reason="insult")

    res = client.post(
        f"{API}/moderation/content/card/{card_id}/delete", json={"reason": "Нарушение"}, headers=mod
    )
    assert res.status_code == 204

    assert count(CatalogItem, CatalogItem.id == card_id) == 0
    assert count(Review) == 0
    assert count(Rating) == 0
    assert count(ShelfEntry) == 0
    assert count(Report) == 0
    assert count(ListItem, ListItem.list_id == list_id) == 1  # чужая позиция осталась
    assert reader_id


def test_hide_endpoint_rejects_profiles_and_unknown_types(client):
    mod = make_moderator(client)
    url = f"{API}/moderation/content/profile/1/hide"
    assert client.post(url, json={"reason": "x"}, headers=mod).status_code == 422
    assert (
        client.post(
            f"{API}/moderation/content/review/999/hide", json={"reason": "x"}, headers=mod
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"{API}/moderation/content/review/1/hide", json={"reason": ""}, headers=mod
        ).status_code
        == 422
    )


def test_pending_cards_queue_approve_reject(client):
    author_id, author = register(client, "author")
    mod = make_moderator(client)
    ok_card = add_card("Одобрить", status=MODERATION_PENDING, local=True, creator=author_id)
    bad_card = add_card("Отклонить", status=MODERATION_PENDING, local=True, creator=author_id)
    add_card("Внешняя")  # не локальная и не на проверке: в очередь не попадает

    queue = client.get(f"{API}/moderation/cards", headers=mod).json()
    assert [c["title"] for c in queue] == ["Одобрить", "Отклонить"]
    assert queue[0]["author_login"] == "author"
    assert client.get(f"{API}/moderation/cards", headers=author).status_code == 403

    # до подтверждения гость карточку не видит
    assert client.get(f"{API}/catalog/{ok_card}").status_code == 404
    assert client.post(f"{API}/moderation/cards/{ok_card}/approve", headers=mod).status_code == 204
    assert client.get(f"{API}/catalog/{ok_card}").status_code == 200  # после — видит

    assert (
        client.post(
            f"{API}/moderation/cards/{bad_card}/reject", json={"reason": ""}, headers=mod
        ).status_code
        == 422
    )
    rejected = client.post(
        f"{API}/moderation/cards/{bad_card}/reject", json={"reason": "Дубль"}, headers=mod
    )
    assert rejected.status_code == 204
    assert client.get(f"{API}/catalog/{bad_card}").status_code == 404

    async def _status(s):
        return (await s.get(CatalogItem, bad_card)).moderation_status

    assert db_run(_status) == MODERATION_HIDDEN
    assert client.post(f"{API}/moderation/cards/{ok_card}/approve", headers=mod).status_code == 409
    assert client.get(f"{API}/moderation/cards", headers=mod).json() == []


def test_every_moderator_action_is_logged(client):
    author_id, _ = register(client, "author")
    _, reporter = register(client, "reporter")
    mod = make_moderator(client, "modname")
    card_id = add_card("К", status=MODERATION_PENDING, local=True, creator=author_id)
    client.post(f"{API}/moderation/cards/{card_id}/approve", headers=mod)
    rep = report(client, reporter, "card", card_id).json()["id"]
    client.post(f"{API}/moderation/reports/{rep}/resolve", json={"decision": "reject"}, headers=mod)
    client.post(f"{API}/moderation/content/card/{card_id}/hide", json={"reason": "r"}, headers=mod)

    async def _actions(s):
        return sorted((await s.scalars(select(AuditLog.action))).all())

    assert db_run(_actions) == ["card.approve", "content.hide", "report.resolve"]

    async def _actors(s):
        return set((await s.scalars(select(AuditLog.actor_login))).all())

    assert db_run(_actors) == {"modname"}
