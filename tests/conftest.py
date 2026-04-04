import pytest
from peewee import SqliteDatabase

from app import create_app
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
