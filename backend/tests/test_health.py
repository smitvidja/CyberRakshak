from fastapi.testclient import TestClient

from app.main import app


def test_health_check_returns_application_status() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "environment": "development"}

def test_root_returns_service_links() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["health"] == "/health"
    assert response.json()["docs"] == "/docs"
