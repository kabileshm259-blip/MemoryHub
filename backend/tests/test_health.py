from fastapi.testclient import TestClient


def test_existing_root_endpoint_still_works(client: TestClient):
    """13a. Preserved root endpoint returns greeting and metadata."""
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["message"] == "Welcome to MemoryHub API"
    assert data["service"] == "memoryhub-api"
    assert data["version"] == "0.1.0"


def test_existing_health_liveness_endpoints_still_work(client: TestClient):
    """13b. Liveness probe endpoints return 200 OK."""
    for path in ["/health", "/health/liveness"]:
        res = client.get(path)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["service"] == "memoryhub-api"


def test_existing_health_readiness_endpoints_still_work(client: TestClient, monkeypatch):
    """13c. Readiness check endpoints return status 'ready' when dependencies are up."""
    from app import main
    monkeypatch.setattr(main, "check_postgres_connection", lambda: True)
    for path in ["/health/readiness", "/ready"]:
        res = client.get(path)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ready"
        assert data["postgres"] == "connected"
