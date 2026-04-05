"""
Integration tests for URL operations.
Tests the full flow of shorten, update, and delete operations.
"""

from app.models.event import Event


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
    user = _create_user_with_api_key(client, "test7", "test7@example.com")
    client.post("/shorten", json={
        "original_url": "https://example.com/list",
        "title": "List test",
    }, headers={"X-API-Key": user["api_key"]})

    response = client.get("/urls")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_list_urls_by_user_and_active_status(client):
    user = _create_user_with_api_key(client, "test7b", "test7b@example.com")
    active = client.post("/urls", json={
        "user_id": user["id"],
        "original_url": "https://example.com/active",
        "title": "Active URL",
    })
    inactive = client.post("/urls", json={
        "user_id": user["id"],
        "original_url": "https://example.com/inactive",
        "title": "Inactive URL",
    })
    client.put(f"/urls/{inactive.get_json()['id']}", json={"is_active": False})

    response = client.get(f"/urls?user_id={user['id']}&is_active=true")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert all(item["user_id"] == user["id"] for item in data)
    assert all(item["is_active"] is True for item in data)
    assert any(item["short_code"] == active.get_json()["short_code"] for item in data)


def test_list_urls_accepts_json_body_filters(client):
    user = _create_user_with_api_key(client, "test7c", "test7c@example.com")
    active = client.post("/urls", json={
        "user_id": user["id"],
        "original_url": "https://example.com/body-active",
        "title": "Body Active URL",
    })
    inactive = client.post("/urls", json={
        "user_id": user["id"],
        "original_url": "https://example.com/body-inactive",
        "title": "Body Inactive URL",
    })
    client.put(f"/urls/{inactive.get_json()['id']}", json={"is_active": False})

    response = client.get("/urls", json={"user_id": user["id"], "is_active": "true"})
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert all(item["user_id"] == user["id"] for item in data)
    assert all(item["is_active"] is True for item in data)
    assert any(item["short_code"] == active.get_json()["short_code"] for item in data)


def test_create_url_via_urls_endpoint(client):
    user = _create_user_with_api_key(client, "test8", "test8@example.com")
    response = client.post("/urls", json={
        "user_id": user["id"],
        "original_url": "https://example.com/from-urls-endpoint",
        "title": "Urls endpoint",
    })

    assert response.status_code == 201
    data = response.get_json()
    assert data["short_code"]
    assert data["redirect_url"].endswith(f"/urls/{data['short_code']}/redirect")


def test_create_url_idempotent(client):
    user = _create_user_with_api_key(client, "test8b", "test8b@example.com")
    payload = {
        "user_id": user["id"],
        "original_url": "https://example.com/idempotent-url",
        "title": "Idempotent URL",
    }

    first_response = client.post("/urls", json=payload)
    assert first_response.status_code == 201
    first_data = first_response.get_json()

    second_response = client.post("/urls", json=payload)
    assert second_response.status_code == 200
    second_data = second_response.get_json()

    assert second_data["was_existing"] is True
    assert second_data["short_code"] == first_data["short_code"]
    assert second_data["id"] == first_data["id"]
    assert second_data["redirect_url"].endswith(f"/urls/{second_data['short_code']}/redirect")


def test_update_url_invalid_field(client):
    user = _create_user_with_api_key(client, "test8c", "test8c@example.com")
    create_response = client.post("/urls", json={
        "user_id": user["id"],
        "original_url": "https://example.com/update-invalid",
        "title": "Update Invalid",
    })
    url_id = create_response.get_json()["id"]

    response = client.put(f"/urls/{url_id}", json={"short_code": "hacked"})
    assert response.status_code == 400
    assert "No valid fields" in response.get_json()["error"]


def test_get_url_by_id(client):
    user = _create_user_with_api_key(client, "test9", "test9@example.com")
    create_response = client.post("/urls", json={
        "user_id": user["id"],
        "original_url": "https://example.com/by-id",
        "title": "By ID",
    })
    url_id = create_response.get_json()["id"]

    response = client.get(f"/urls/{url_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == url_id


def test_update_url_via_urls_endpoint(client):
    user = _create_user_with_api_key(client, "test10", "test10@example.com")
    create_response = client.post("/urls", json={
        "user_id": user["id"],
        "original_url": "https://example.com/update-me",
        "title": "Original Title",
    })
    url_id = create_response.get_json()["id"]

    response = client.put(f"/urls/{url_id}", json={"title": "Updated Title"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["title"] == "Updated Title"


def test_delete_url_via_urls_endpoint(client):
    user = _create_user_with_api_key(client, "test11", "test11@example.com")
    create_response = client.post("/urls", json={
        "user_id": user["id"],
        "original_url": "https://example.com/delete-me",
        "title": "Delete Me",
    })
    url_id = create_response.get_json()["id"]

    response = client.delete(f"/urls/{url_id}")
    assert response.status_code == 200
    assert response.get_json()["deleted_url_id"] == url_id


def test_delete_url_cleans_related_events(client):
    user = _create_user_with_api_key(client, "test12", "test12@example.com")
    create_response = client.post("/urls", json={
        "user_id": user["id"],
        "original_url": "https://example.com/delete-events",
        "title": "Delete Events",
    })
    url_id = create_response.get_json()["id"]

    assert Event.select().where(Event.url_id == url_id).count() == 1

    response = client.delete(f"/urls/{url_id}")
    assert response.status_code == 200
    assert Event.select().where(Event.url_id == url_id).count() == 0


def test_redirect_short_code(client):
    user = _create_user_with_api_key(client, "redir_user", "redir_user@example.com")
    create_response = client.post(
        "/urls",
        json={
            "user_id": user["id"],
            "original_url": "https://example.com/redirect-target",
            "title": "Redirect Target",
        },
    )
    short_code = create_response.get_json()["short_code"]

    response = client.get(f"/urls/{short_code}/redirect", follow_redirects=False)
    assert response.status_code in (301, 302)
    assert "Location" in response.headers
    assert "example.com/redirect-target" in response.headers["Location"]


def test_create_url_rejects_non_object_json_payload(client):
    response = client.post(
        "/urls",
        data='"not-an-object"',
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "json object" in response.get_json()["error"].lower()
