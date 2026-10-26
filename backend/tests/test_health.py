def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "sqlite"
    assert data["llm_configured"] is False


def test_openapi_docs_available(client):
    response = client.get("/docs")

    assert response.status_code == 200
