from io import BytesIO

from app.models.event import Event
from app.models.url import Url


def test_create_user(client):
    response = client.post("/users", json={
        "username": "testuser",
        "email": "test@example.com",
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"


def test_create_user_missing_fields(client):
    response = client.post("/users", json={"username": "only_name"})
    assert response.status_code == 400


def test_create_user_duplicate_username(client):
    client.post("/users", json={"username": "dupe", "email": "a@b.com"})
    response = client.post("/users", json={"username": "dupe", "email": "c@d.com"})
    assert response.status_code == 409


def test_create_user_duplicate_email(client):
    client.post("/users", json={"username": "user_a", "email": "same@example.com"})
    response = client.post("/users", json={"username": "user_b", "email": "same@example.com"})
    assert response.status_code == 409


def test_list_users(client):
    client.post("/users", json={"username": "u1", "email": "u1@example.com"})
    client.post("/users", json={"username": "u2", "email": "u2@example.com"})
    response = client.get("/users")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert "users" in data
    assert len(data["users"]) == 2


def test_get_users_pagination(client):
    for index in range(12):
        client.post(
            "/users",
            json={"username": f"paged_{index}", "email": f"paged_{index}@example.com"},
        )

    response = client.get("/users", json={"page": 1, "per_page": 10})
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert len(data["users"]) == 10
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["per_page"] == 10
    assert data["pagination"]["has_more"] is True


def test_update_user_duplicate_email(client):
    first = client.post("/users", json={"username": "first", "email": "first@example.com"})
    client.post("/users", json={"username": "second", "email": "second@example.com"})

    response = client.put(
        f"/users/{first.get_json()['id']}",
        json={"email": "second@example.com"},
    )
    assert response.status_code == 409


def test_update_user(client):
    create_resp = client.post("/users", json={"username": "rename_me", "email": "rename@me.com"})
    user_id = create_resp.get_json()["id"]

    response = client.put(f"/users/{user_id}", json={"username": "updated_username"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == user_id
    assert data["username"] == "updated_username"


def test_delete_user(client):
    create_resp = client.post("/users", json={"username": "delete_me", "email": "delete@me.com"})
    user_id = create_resp.get_json()["id"]

    response = client.delete(f"/users/{user_id}")
    assert response.status_code == 200
    assert response.get_json()["deleted_user_id"] == user_id

    get_response = client.get(f"/users/{user_id}")
    assert get_response.status_code == 404


def test_get_user_by_id(client):
    create_resp = client.post("/users", json={"username": "findme", "email": "find@me.com"})
    user_id = create_resp.get_json()["id"]
    response = client.get(f"/users/{user_id}")
    assert response.status_code == 200
    assert response.get_json()["username"] == "findme"


def test_get_user_not_found(client):
    response = client.get("/users/99999")
    assert response.status_code == 404


def test_bulk_create_users(client):
    csv_data = "username,email\nalpha,alpha@example.com\nbeta,beta@example.com\n"

    response = client.post(
        "/users/bulk",
        data={
            "file": (BytesIO(csv_data.encode("utf-8")), "users.csv"),
            "row_count": "2",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code in (200, 201)
    data = response.get_json()
    assert data["created"] == 2
    assert data["row_count"] == 2

    list_response = client.get("/users")
    assert len(list_response.get_json()["users"]) == 2


def test_bulk_create_users_invalid_row_count(client):
    csv_data = "username,email\nalpha,alpha@example.com\nbeta,beta@example.com\n"

    response = client.post(
        "/users/bulk",
        data={
            "file": (BytesIO(csv_data.encode("utf-8")), "users.csv"),
            "row_count": "3",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "row_count" in response.get_json()["error"]


def test_delete_user_cleans_related_urls_and_events(client, sample_user_with_api_key):
    create_resp = client.post(
        "/urls",
        json={
            "user_id": sample_user_with_api_key["id"],
            "original_url": "https://example.com/delete-cleanup",
            "title": "Cleanup Test",
        },
    )
    url_id = create_resp.get_json()["id"]

    delete_response = client.delete(f"/users/{sample_user_with_api_key['id']}")
    assert delete_response.status_code == 200

    assert client.get(f"/users/{sample_user_with_api_key['id']}").status_code == 404
    assert Url.select().where(Url.id == url_id).count() == 0
    assert Url.select().where(Url.user_id == sample_user_with_api_key["id"]).count() == 0
    assert Event.select().where(Event.user_id == sample_user_with_api_key["id"]).count() == 0
