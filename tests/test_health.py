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


def test_metrics_endpoint_exposes_prometheus_metrics(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.data.decode("utf-8")
    assert "http_requests_total" in body
    assert "http_request_duration_seconds" in body
    assert "process_resident_memory_bytes" in body
