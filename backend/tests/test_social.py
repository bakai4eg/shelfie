"""Тесты подписок (ТЗ 4.2.3, 4.5.4)."""

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


def test_follow_unfollow_and_counters(client):
    u1 = register(client, "alice")
    register(client, "bob")
    h1 = auth(u1["access_token"])

    # нельзя подписаться на самого себя
    res_self = client.post(f"{API}/users/alice/follow", headers=h1)
    assert res_self.status_code == 400

    # alice подписывается на bob
    res_follow = client.post(f"{API}/users/bob/follow", headers=h1)
    assert res_follow.status_code == 200
    assert res_follow.json()["is_following"] is True
    assert res_follow.json()["followers"] == 1

    # проверяем профиль bob глазами alice
    p_bob_for_alice = client.get(f"{API}/users/bob", headers=h1).json()
    assert p_bob_for_alice["is_following"] is True
    assert p_bob_for_alice["stats"]["followers"] == 1

    # проверяем профиль bob глазами гостя
    p_bob_guest = client.get(f"{API}/users/bob").json()
    assert p_bob_guest["is_following"] is False
    assert p_bob_guest["stats"]["followers"] == 1

    # проверяем профиль alice (1 following)
    p_alice = client.get(f"{API}/users/alice").json()
    assert p_alice["stats"]["following"] == 1

    # список подписчиков bob
    followers = client.get(f"{API}/users/bob/followers").json()
    assert len(followers) == 1
    assert followers[0]["login"] == "alice"

    # отписка
    res_unfollow = client.delete(f"{API}/users/bob/follow", headers=h1)
    assert res_unfollow.status_code == 200
    assert res_unfollow.json()["is_following"] is False

    # профиль bob обновился
    p_bob_after = client.get(f"{API}/users/bob").json()
    assert p_bob_after["stats"]["followers"] == 0
