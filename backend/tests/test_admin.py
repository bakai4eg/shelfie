"""T5.1 и T5.2: управление пользователями, сводка и журнал (ТЗ 4.6.4, 4.6.5)."""

import asyncio
from datetime import date, timedelta

from sqlalchemy import func, select

from app.core.constants import MODERATION_APPROVED, ROLE_ADMIN
from app.db.session import get_session
from app.main import app
from app.models.audit import AuditLog
from app.models.catalog import CatalogItem
from app.models.library import Rating, ShelfEntry
from app.models.lists import ListItem, UserList
from app.models.moderation import Report
from app.models.social import Follow, Review
from app.models.user import Session as AuthSession
from app.models.user import User

API = "/api"


def register(client, login):
    res = client.post(
        f"{API}/auth/register",
        json={"login": login, "email": f"{login}@example.com", "password": "secret123"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    return body["user"]["id"], {"Authorization": f"Bearer {body['access_token']}"}


def db_run(coro_fn):
    async def _go():
        async for session in app.dependency_overrides[get_session]():
            return await coro_fn(session)

    return asyncio.run(_go())


def set_role(user_id, role):
    async def _set(s):
        (await s.get(User, user_id)).role = role
        await s.commit()

    db_run(_set)


def make_admin(client, login="boss"):
    user_id, headers = register(client, login)
    set_role(user_id, ROLE_ADMIN)
    return user_id, headers


def count(model, *where):
    async def _count(s):
        return await s.scalar(select(func.count()).select_from(model).where(*where))

    return db_run(_count)


def add_card(title="Фильм", local=False, creator=None, poster=None):
    async def _add(s):
        item = CatalogItem(
            type="movie",
            title=title,
            moderation_status=MODERATION_APPROVED,
            is_local=local,
            source="local" if local else "tmdb",
            external_id=None if local else title,
            created_by=creator,
            poster_path=poster,
        )
        s.add(item)
        await s.commit()
        await s.refresh(item)
        return item.id

    return db_run(_add)


def test_admin_routes_closed_to_non_admins(client):
    guest = client.get(f"{API}/admin/users")
    assert guest.status_code == 401
    _, user = register(client, "plain")
    mod_id, mod = register(client, "moder")
    set_role(mod_id, "moderator")

    for headers in (user, mod):
        assert client.get(f"{API}/admin/users", headers=headers).status_code == 403
        assert client.get(f"{API}/admin/summary", headers=headers).status_code == 403
        assert client.get(f"{API}/admin/audit", headers=headers).status_code == 403


def test_users_list_search_and_filters(client):
    _, boss = make_admin(client)
    register(client, "alice")
    bob_id, _ = register(client, "bobby")
    client.post(f"{API}/admin/users/{bob_id}/block", headers=boss)

    everyone = client.get(f"{API}/admin/users", headers=boss).json()
    assert everyone["total"] == 3
    assert "password_hash" not in everyone["items"][0]

    assert [
        u["login"] for u in client.get(f"{API}/admin/users?q=ALI", headers=boss).json()["items"]
    ] == ["alice"]
    blocked = client.get(f"{API}/admin/users?is_blocked=true", headers=boss).json()
    assert [u["login"] for u in blocked["items"]] == ["bobby"]
    admins = client.get(f"{API}/admin/users?role=admin", headers=boss).json()
    assert [u["login"] for u in admins["items"]] == ["boss"]


def test_moderator_role_granted_and_revoked_immediately(client):
    _, boss = make_admin(client)
    user_id, user = register(client, "newmod")

    assert client.get(f"{API}/moderation/reports", headers=user).status_code == 403
    res = client.patch(
        f"{API}/admin/users/{user_id}/role", json={"role": "moderator"}, headers=boss
    )
    assert res.status_code == 200 and res.json()["role"] == "moderator"
    assert client.get(f"{API}/moderation/reports", headers=user).status_code == 200

    client.patch(f"{API}/admin/users/{user_id}/role", json={"role": "user"}, headers=boss)
    assert client.get(f"{API}/moderation/reports", headers=user).status_code == 403  # сразу закрыт

    # администратора через API назначить нельзя
    bad = client.patch(f"{API}/admin/users/{user_id}/role", json={"role": "admin"}, headers=boss)
    assert bad.status_code == 422


def test_blocked_user_cannot_login_and_loses_sessions(client):
    _, boss = make_admin(client)
    user_id, user = register(client, "victim")
    assert client.get(f"{API}/auth/me", headers=user).status_code == 200

    assert client.post(f"{API}/admin/users/{user_id}/block", headers=boss).status_code == 200

    # старый токен больше не работает
    assert client.get(f"{API}/auth/me", headers=user).status_code in (401, 403)
    login = client.post(f"{API}/auth/login", json={"login": "victim", "password": "secret123"})
    assert login.status_code == 403
    assert login.json()["detail"] == "Аккаунт заблокирован"

    client.post(f"{API}/admin/users/{user_id}/unblock", headers=boss)
    again = client.post(f"{API}/auth/login", json={"login": "victim", "password": "secret123"})
    assert again.status_code == 200


def test_admin_cannot_touch_self_or_other_admins(client):
    boss_id, boss = make_admin(client)
    other_id, _ = make_admin(client, "boss2")

    for path, method in (
        (f"/admin/users/{boss_id}/block", "post"),
        (f"/admin/users/{boss_id}/unblock", "post"),
        (f"/admin/users/{boss_id}", "delete"),
        (f"/admin/users/{other_id}/block", "post"),
        (f"/admin/users/{other_id}", "delete"),
    ):
        assert getattr(client, method)(f"{API}{path}", headers=boss).status_code == 409, path
    own_role = client.patch(
        f"{API}/admin/users/{boss_id}/role", json={"role": "user"}, headers=boss
    )
    assert own_role.status_code == 409
    assert client.post(f"{API}/admin/users/9999/block", headers=boss).status_code == 404


def test_delete_user_removes_everything(client, tmp_path, monkeypatch):
    boss_id, boss = make_admin(client)
    victim_id, victim = register(client, "victim")
    friend_id, friend = register(client, "friend")

    poster = tmp_path / "cover.png"
    poster.write_bytes(b"png")
    monkeypatch.setattr("app.core.media._root", lambda: tmp_path)

    own_card = add_card("Своя", local=True, creator=victim_id, poster="cover.png")
    common = add_card("Общая")
    client.post(
        f"{API}/catalog/{common}/reviews",
        json={"title": "Т", "body": "Б", "rating": 7},
        headers=victim,
    )
    client.post(
        f"{API}/catalog/{own_card}/reviews", json={"title": "Т2", "body": "Б2"}, headers=friend
    )
    client.put(f"{API}/me/ratings/{common}", json={"value": 10}, headers=victim)
    client.put(f"{API}/me/ratings/{common}", json={"value": 4}, headers=friend)
    client.put(f"{API}/me/library/{common}", json={"status": "planned"}, headers=victim)
    list_id = client.post(f"{API}/me/lists", json={"title": "L"}, headers=victim).json()["id"]
    client.post(f"{API}/me/lists/{list_id}/items", json={"item_id": common}, headers=victim)
    client.post(f"{API}/users/friend/follow", headers=victim)
    client.post(f"{API}/users/victim/follow", headers=friend)
    client.post(
        f"{API}/reports",
        json={"target_type": "profile", "target_id": victim_id, "reason": "spam"},
        headers=friend,
    )

    assert count(Follow) == 2 and count(Report) == 1 and count(ListItem) == 1
    client.post(f"{API}/admin/users/{victim_id}/block", headers=boss)
    assert count(AuthSession, AuthSession.user_id == victim_id) > 0

    res = client.delete(f"{API}/admin/users/{victim_id}", headers=boss)
    assert res.status_code == 204

    assert count(User, User.id == victim_id) == 0
    assert count(Review, Review.user_id == victim_id) == 0
    assert count(Review, Review.item_id == own_card) == 0  # чужая рецензия на удалённую карточку
    assert count(CatalogItem, CatalogItem.id == own_card) == 0
    assert count(Rating, Rating.user_id == victim_id) == 0
    assert count(ShelfEntry, ShelfEntry.user_id == victim_id) == 0
    assert count(UserList, UserList.user_id == victim_id) == 0
    assert count(ListItem) == 0
    assert count(Follow) == 0
    assert count(AuthSession, AuthSession.user_id == victim_id) == 0
    assert count(Report) == 0
    assert not poster.exists()  # файл обложки удалён

    async def _avg(s):
        item = await s.get(CatalogItem, common)
        return float(item.rating_avg), item.ratings_count

    assert db_run(_avg) == (4.0, 1)  # рейтинг пересчитан без удалённого
    assert client.get(f"{API}/users/victim").status_code == 404
    assert client.get(f"{API}/auth/me", headers=victim).status_code == 401


def test_summary_matches_real_data(client):
    boss_id, boss = make_admin(client)
    author_id, author = register(client, "author")
    _, reporter = register(client, "reporter")
    card = add_card("К1")
    add_card("К2")
    review = client.post(
        f"{API}/catalog/{card}/reviews", json={"title": "Т", "body": "Б"}, headers=author
    ).json()["id"]
    client.post(
        f"{API}/reports",
        json={"target_type": "review", "target_id": review, "reason": "spam"},
        headers=reporter,
    )

    assert client.get(f"{API}/admin/summary", headers=boss).json() == {
        "users": 3,
        "cards": 2,
        "reviews": 1,
        "open_reports": 1,
    }

    client.delete(f"{API}/admin/users/{author_id}", headers=boss)
    assert client.get(f"{API}/admin/summary", headers=boss).json() == {
        "users": 2,
        "cards": 2,
        "reviews": 0,
        "open_reports": 0,
    }


def test_audit_log_content_filters_and_survives_deleted_actor(client):
    boss_id, boss = make_admin(client)
    mod_id, mod = register(client, "moder")
    set_role(mod_id, "moderator")
    victim_id, _ = register(client, "victim")

    client.post(f"{API}/admin/users/{victim_id}/block", headers=boss)
    client.patch(f"{API}/admin/users/{mod_id}/role", json={"role": "moderator"}, headers=boss)
    client.delete(f"{API}/admin/users/{victim_id}", headers=boss)

    log = client.get(f"{API}/admin/audit", headers=boss).json()
    assert log["total"] == 3
    newest = log["items"][0]
    assert (
        newest["action"],
        newest["actor_login"],
        newest["target_type"],
        newest["target_id"],
    ) == (
        "user.delete",
        "boss",
        "user",
        victim_id,
    )
    assert newest["created_at"]
    role_entry = next(i for i in log["items"] if i["action"] == "user.role")
    assert (
        role_entry["details"]["before"] == "moderator"
        and role_entry["details"]["after"] == "moderator"
    )

    only_blocks = client.get(f"{API}/admin/audit?action=user.block", headers=boss).json()
    assert [i["action"] for i in only_blocks["items"]] == ["user.block"]
    assert client.get(f"{API}/admin/audit?actor=nobody", headers=boss).json()["total"] == 0
    assert client.get(f"{API}/admin/audit?actor=BOS", headers=boss).json()["total"] == 3

    today = date.today()
    start, end = today - timedelta(days=1), today + timedelta(days=1)
    in_range = client.get(
        f"{API}/admin/audit?date_from={start}&date_to={end}", headers=boss
    ).json()
    assert in_range["total"] == 3
    past = client.get(f"{API}/admin/audit?date_to={today - timedelta(days=2)}", headers=boss).json()
    assert past["total"] == 0

    paged = client.get(f"{API}/admin/audit?size=2&page=2", headers=boss).json()
    assert len(paged["items"]) == 1 and paged["total"] == 3

    # автор действия удалён: журнал не ломается, логин сохраняется копией
    other_id, _ = make_admin(client, "boss2")
    client.post(f"{API}/admin/users/{mod_id}/block", headers=boss)  # ещё одна запись
    set_role(boss_id, "user")  # чтобы разрешить удаление первого админа вторым
    token = client.post(
        f"{API}/auth/login", json={"login": "boss2", "password": "secret123"}
    ).json()["access_token"]
    second = {"Authorization": f"Bearer {token}"}
    assert client.delete(f"{API}/admin/users/{boss_id}", headers=second).status_code == 204

    after = client.get(f"{API}/admin/audit", headers=second)
    assert after.status_code == 200
    by_old_actor = [i for i in after.json()["items"] if i["actor_login"] == "boss"]
    assert by_old_actor and all(i["actor_id"] is None for i in by_old_actor)
    assert other_id


def test_every_admin_action_is_logged(client):
    _, boss = make_admin(client)
    user_id, _ = register(client, "target")
    client.patch(f"{API}/admin/users/{user_id}/role", json={"role": "moderator"}, headers=boss)
    client.post(f"{API}/admin/users/{user_id}/block", headers=boss)
    client.post(f"{API}/admin/users/{user_id}/unblock", headers=boss)

    async def _actions(s):
        return sorted((await s.scalars(select(AuditLog.action))).all())

    assert db_run(_actions) == ["user.block", "user.role", "user.unblock"]
