def test_get_events_list(client):
    client.post("/seed")

    response = client.get("/events")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)


def test_get_events_by_url(client):
    client.post("/seed")

    response = client.get("/events", json={"url_id": 1})
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert all(event["url_id"] == 1 for event in data)


def test_get_events_by_user(client):
    client.post("/seed")

    response = client.get("/events", json={"user_id": 1})
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert all(event["user_id"] == 1 for event in data)


def test_get_events_by_type(client):
    client.post("/seed")

    response = client.get("/events", json={"event_type": "created"})
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert all(event["event_type"] == "created" for event in data)


def test_create_event(client):
    client.post("/seed")

    response = client.post("/events", json={
        "url_id": 1,
        "user_id": 1,
        "event_type": "click",
        "details": {"referrer": "https://google.com"},
    })

    assert response.status_code == 201
    data = response.get_json()
    assert data["event_type"] == "click"
    assert data["url_id"] == 1
    assert data["user_id"] == 1
    assert isinstance(data["details"], dict)
    assert data["details"]["referrer"] == "https://google.com"


def test_get_events_limit_returns_newest_first(client):
    client.post("/seed")
    client.post("/events", json={
        "url_id": 1,
        "user_id": 1,
        "event_type": "click",
        "details": {"kind": "first"},
    })
    client.post("/events", json={
        "url_id": 1,
        "user_id": 1,
        "event_type": "click",
        "details": {"kind": "second"},
    })

    response = client.get("/events", json={"limit": 1})
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["event_type"] == "click"
    assert data[0]["details"].get("kind") == "second"
