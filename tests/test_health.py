import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"

def test_ready_check(client):
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"

def test_404_returns_json(client):
    response = client.get("/nonexistent-route")
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "Not found"
    assert data["status"] == 404

def test_405_returns_json(client):
    response = client.delete("/health")
    assert response.status_code == 405
    data = response.get_json()
    assert data["error"] == "Method not allowed"
    assert data["status"] == 405