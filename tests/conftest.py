import pytest
import time
from peewee import SqliteDatabase

from app import create_app
from app import cache as cache_module
from app.database import db
from app.models.user import User
from app.models.url import Url
from app.models.event import Event

# WHY SQLite in-memory: Tests run fast without needing a real PostgreSQL.
# Per DECISIONS.md #6 — SQLite for test speed, PostgreSQL for production.
test_db = SqliteDatabase(":memory:")


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True

    # Swap the DB proxy to point at in-memory SQLite
    test_db.bind([User, Url, Event])
    test_db.connect()
    test_db.create_tables([User, Url, Event])

    yield app

    test_db.drop_tables([Event, Url, User])
    test_db.close()


@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client


class _NullRedis:
    def get(self, key):
        return None

    def setex(self, key, ttl, value):
        return True

    def keys(self, pattern):
        return []

    def delete(self, *keys):
        return 0

    def ping(self):
        return True


@pytest.fixture(autouse=True)
def disable_real_redis():
    original_client = cache_module._redis_client
    cache_module._redis_client = _NullRedis()
    yield
    cache_module._redis_client = original_client


@pytest.fixture
def sample_user(client):
    timestamp = int(time.time() * 1000)
    response = client.post(
        "/users",
        json={
            "username": f"testuser_{timestamp}",
            "email": f"testuser_{timestamp}@test.com",
        },
    )
    return response.get_json()


@pytest.fixture
def sample_url(client, sample_user):
    timestamp = int(time.time() * 1000)
    response = client.post(
        "/shorten",
        json={
            "user_id": sample_user["id"],
            "original_url": f"https://example.com/test/{timestamp}",
            "title": f"Test URL {timestamp}",
        },
    )
    return response.get_json()
