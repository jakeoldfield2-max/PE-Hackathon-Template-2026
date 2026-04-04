def _create_user(client, username="testuser", email="test@example.com"):
    resp = client.post("/users", json={"username": username, "email": email})
    return resp.get_json()["id"]


def test_shorten_url(client):
    user_id = _create_user(client)
    response = client.post("/shorten", json={
        "user_id": user_id,
        "original_url": "https://example.com",
        "title": "Example",
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data["original_url"] == "https://example.com"
    assert data["title"] == "Example"
    assert len(data["short_code"]) == 6


def test_shorten_url_missing_fields(client):
    response = client.post("/shorten", json={"user_id": 1})
    assert response.status_code == 400


def test_shorten_url_user_not_found(client):
    response = client.post("/shorten", json={
        "user_id": 99999,
        "original_url": "https://example.com",
        "title": "Test",
    })
    assert response.status_code == 404


def test_update_url(client):
    user_id = _create_user(client)
    create_resp = client.post("/shorten", json={
        "user_id": user_id,
        "original_url": "https://example.com",
        "title": "Old Title",
    })
    url_id = create_resp.get_json()["id"]

    response = client.post("/update", json={
        "user_id": user_id,
        "url_id": url_id,
        "field": "title",
        "new_value": "New Title",
    })
    assert response.status_code == 200
    assert response.get_json()["new_value"] == "New Title"


def test_update_url_invalid_field(client):
    user_id = _create_user(client)
    create_resp = client.post("/shorten", json={
        "user_id": user_id,
        "original_url": "https://example.com",
        "title": "Test",
    })
    url_id = create_resp.get_json()["id"]

    response = client.post("/update", json={
        "user_id": user_id,
        "url_id": url_id,
        "field": "short_code",
        "new_value": "hacked",
    })
    assert response.status_code == 400


def test_delete_url(client):
    user_id = _create_user(client)
    client.post("/shorten", json={
        "user_id": user_id,
        "original_url": "https://example.com",
        "title": "DeleteMe",
    })

    response = client.post("/delete", json={
        "user_id": user_id,
        "title": "DeleteMe",
    })
    assert response.status_code == 200
    assert response.get_json()["message"] == "URL deleted successfully"


def test_delete_url_not_found(client):
    user_id = _create_user(client)
    response = client.post("/delete", json={
        "user_id": user_id,
        "title": "NonExistent",
    })
    assert response.status_code == 404
