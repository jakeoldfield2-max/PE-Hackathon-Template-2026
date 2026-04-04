"""
Integration tests for URL operations.
Tests the full flow of shorten, update, and delete operations.
"""


def _create_user_with_api_key(client, username="testuser", email="test@example.com"):
    """Create a user and generate an API key for them."""
    resp = client.post("/users", json={"username": username, "email": email})
    user = resp.get_json()
    # Generate API key
    key_resp = client.post(f"/users/{user['id']}/api-key")
    user["api_key"] = key_resp.get_json()["api_key"]
    return user


def test_shorten_url(client):
    user = _create_user_with_api_key(client)
    response = client.post("/shorten", json={
        "original_url": "https://example.com",
        "title": "Example",
    }, headers={"X-API-Key": user["api_key"]})
    assert response.status_code == 201
    data = response.get_json()
    assert data["original_url"] == "https://example.com"
    assert data["title"] == "Example"
    assert len(data["short_code"]) == 6


def test_shorten_url_missing_fields(client):
    user = _create_user_with_api_key(client, "test2", "test2@example.com")
    response = client.post("/shorten", json={},
                           headers={"X-API-Key": user["api_key"]})
    assert response.status_code == 400


def test_shorten_url_no_api_key(client):
    """Test that shorten fails without API key."""
    response = client.post("/shorten", json={
        "original_url": "https://example.com",
        "title": "Test",
    })
    assert response.status_code == 401


def test_update_url(client):
    user = _create_user_with_api_key(client, "test3", "test3@example.com")
    create_resp = client.post("/shorten", json={
        "original_url": "https://example.com",
        "title": "Old Title",
    }, headers={"X-API-Key": user["api_key"]})
    url_id = create_resp.get_json()["id"]

    response = client.post("/update", json={
        "user_id": user["id"],
        "url_id": url_id,
        "field": "title",
        "new_value": "New Title",
    })
    assert response.status_code == 200
    assert response.get_json()["new_value"] == "New Title"


def test_update_url_invalid_field(client):
    user = _create_user_with_api_key(client, "test4", "test4@example.com")
    create_resp = client.post("/shorten", json={
        "original_url": "https://example.com",
        "title": "Test",
    }, headers={"X-API-Key": user["api_key"]})
    url_id = create_resp.get_json()["id"]

    response = client.post("/update", json={
        "user_id": user["id"],
        "url_id": url_id,
        "field": "short_code",
        "new_value": "hacked",
    })
    assert response.status_code == 400


def test_delete_url(client):
    user = _create_user_with_api_key(client, "test5", "test5@example.com")
    client.post("/shorten", json={
        "original_url": "https://example.com",
        "title": "DeleteMe",
    }, headers={"X-API-Key": user["api_key"]})

    response = client.post("/delete", json={
        "user_id": user["id"],
        "title": "DeleteMe",
    })
    assert response.status_code == 200
    assert response.get_json()["message"] == "URL deleted successfully"


def test_delete_url_not_found(client):
    user = _create_user_with_api_key(client, "test6", "test6@example.com")
    response = client.post("/delete", json={
        "user_id": user["id"],
        "title": "NonExistent",
    })
    assert response.status_code == 404


def test_list_urls(client):
    user_id = _create_user(client)
    client.post("/shorten", json={
        "user_id": user_id,
        "original_url": "https://example.com/list",
        "title": "List test",
    })

    response = client.get("/urls")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert "urls" in data
    assert len(data["urls"]) >= 1
