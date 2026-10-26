def test_health(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_docs_available(client):
    assert client.get("/docs").status_code == 200
