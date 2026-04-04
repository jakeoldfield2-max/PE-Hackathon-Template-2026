def test_seed_creates_demo_data(client):
    response = client.post("/seed")
    assert response.status_code == 201
    data = response.get_json()
    assert data["users_created"] == 3
    assert data["urls_created"] == 10
    assert data["events_created"] == 10


def test_seed_is_idempotent(client):
    client.post("/seed")
    response = client.post("/seed")
    assert response.status_code == 201
    data = response.get_json()
    assert data["users_created"] == 3


def test_stats_after_seed(client):
    client.post("/seed")
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.get_json()
    assert data["total_users"] == 3
    assert data["total_urls"] == 10
    assert data["active_urls"] == 10
    assert data["total_events"] == 10
    assert data["events_by_type"]["created"] == 10


def test_stats_empty(client):
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.get_json()
    assert data["total_users"] == 0
    assert data["total_urls"] == 0
