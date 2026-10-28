"""Тесты жалоб и модерации (ТЗ 4.6.2, 4.6.3)."""

import asyncio

from app.core.constants import MODERATION_APPROVED, ROLE_MODERATOR
from app.db.session import get_session
from app.main import app
from app.models.catalog import CatalogItem
from app.models.user import User

API = "/api"


def register(client, login: str) -> dict:
    res = client.post(
        f"{API}/auth/register",
        json={"login": login, "email": f"{login.lower()}@example.com", "password": "secret123"},
    )
    assert res.status_code == 201, res.text
    return res.json()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def make_moderator(user_id: int):
    async def _make():
        async for session in app.dependency_overrides[get_session]():
            user = await session.get(User, user_id)
            user.role = ROLE_MODERATOR
            await session.commit()
            return

    asyncio.run(_make())


def add_card(title: str = "Криминальное чтиво") -> int:
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


def test_reports_lifecycle(client):
    author = register(client, "author")
    reporter = register(client, "reporter")
    mod = register(client, "mod")
    make_moderator(mod["user"]["id"])

    h_author = auth(author["access_token"])
    h_reporter = auth(reporter["access_token"])
    h_mod = auth(mod["access_token"])

    item_id = add_card("Фильм с рецензией")

    # Создаём рецензию
    rev_res = client.post(
        f"{API}/catalog/{item_id}/reviews",
        json={"title": "Спам рецензия", "body": "Реклама казино", "rating": 1},
        headers=h_author,
    )
    rev_id = rev_res.json()["id"]

    # Отправляем жалобу
    report_res = client.post(
        f"{API}/reports",
        json={
            "target_type": "review",
            "target_id": rev_id,
            "reason": "spam",
            "comment": "Тут реклама",
        },
        headers=h_reporter,
    )
    assert report_res.status_code == 201, report_res.text
    rep_id = report_res.json()["id"]

    # Дубль даёт 409
    dup_res = client.post(
        f"{API}/reports",
        json={"target_type": "review", "target_id": rev_id, "reason": "spam"},
        headers=h_reporter,
    )
    assert dup_res.status_code == 409

    # Репортер видит свои жалобы
    my_reports = client.get(f"{API}/me/reports", headers=h_reporter).json()
    assert len(my_reports) == 1
    assert my_reports[0]["id"] == rep_id

    # Обычный юзер не имеет доступа к модерации (403)
    assert client.get(f"{API}/moderation/reports", headers=h_reporter).status_code == 403

    # Модератор видит очередь
    queue = client.get(f"{API}/moderation/reports", headers=h_mod)
    assert queue.status_code == 200
    assert len(queue.json()) == 1
    assert queue.json()[0]["id"] == rep_id

    # Модератор скрывает рецензию (hide)
    resolve_res = client.post(
        f"{API}/moderation/reports/{rep_id}/resolve",
        json={"decision": "hide", "reason": "Спам удалён"},
        headers=h_mod,
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "resolved"
    assert resolve_res.json()["resolution"] == "hide"

    # Рецензия исчезла из публичного списка
    public_revs = client.get(f"{API}/catalog/{item_id}/reviews").json()
    assert public_revs["total"] == 0
