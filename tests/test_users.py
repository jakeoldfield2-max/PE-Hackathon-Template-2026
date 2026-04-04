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


def test_list_users(client):
    client.post("/users", json={"username": "u1", "email": "u1@example.com"})
    client.post("/users", json={"username": "u2", "email": "u2@example.com"})
    response = client.get("/users")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert "users" in data
    assert len(data["users"]) == 2


def test_get_user_by_id(client):
    create_resp = client.post("/users", json={"username": "findme", "email": "find@me.com"})
    user_id = create_resp.get_json()["id"]
    response = client.get(f"/users/{user_id}")
    assert response.status_code == 200
    assert response.get_json()["username"] == "findme"


def test_get_user_not_found(client):
    response = client.get("/users/99999")
    assert response.status_code == 404
