import json
import random
import string
from datetime import datetime, timedelta

from flask import Blueprint, jsonify

from app.database import db
from app.models.user import User
from app.models.url import Url
from app.models.event import Event

seed_bp = Blueprint("seed", __name__)

DEMO_USERS = [
    {"username": "alice", "email": "alice@example.com"},
    {"username": "bob", "email": "bob@example.com"},
    {"username": "charlie", "email": "charlie@example.com"},
]

DEMO_URLS = [
    {"original_url": "https://github.com/MLH/mlh-policies", "title": "MLH Policies"},
    {"original_url": "https://flask.palletsprojects.com/", "title": "Flask Docs"},
    {"original_url": "https://docs.peewee-orm.com/", "title": "Peewee Docs"},
    {"original_url": "https://prometheus.io/docs/", "title": "Prometheus Docs"},
    {"original_url": "https://grafana.com/docs/", "title": "Grafana Docs"},
    {"original_url": "https://k6.io/docs/", "title": "k6 Load Testing"},
    {"original_url": "https://nginx.org/en/docs/", "title": "Nginx Docs"},
    {"original_url": "https://redis.io/docs/", "title": "Redis Docs"},
    {"original_url": "https://www.docker.com/get-started", "title": "Docker Getting Started"},
    {"original_url": "https://developer.hashicorp.com/terraform", "title": "Terraform Docs"},
]


def _generate_short_code(length=6):
    characters = string.ascii_letters + string.digits
    return "".join(random.choices(characters, k=length))


@seed_bp.route("/seed", methods=["POST"])
def seed():
    """Populate demo data for users, URLs, and events.
    WHY: Demo video is 2 min max — one curl POST /seed populates everything.
    Idempotent: clears existing data first.
    Reference: DEMO_SCRIPT.md step 2.
    """
    with db.atomic():
        Event.delete().execute()
        Url.delete().execute()
        User.delete().execute()

        users = []
        for u in DEMO_USERS:
            user = User.create(
                username=u["username"],
                email=u["email"],
                created_at=datetime.now() - timedelta(days=random.randint(1, 30)),
            )
            users.append(user)

        urls = []
        for i, u in enumerate(DEMO_URLS):
            owner = users[i % len(users)]
            now = datetime.now() - timedelta(hours=random.randint(1, 72))
            url = Url.create(
                user_id=owner,
                short_code=_generate_short_code(),
                original_url=u["original_url"],
                title=u["title"],
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            urls.append(url)

            Event.create(
                url_id=url,
                user_id=owner,
                event_type="created",
                timestamp=now,
                details=json.dumps({"short_code": url.short_code, "original_url": url.original_url}),
            )

    return jsonify({
        "message": "Demo data seeded",
        "users_created": len(users),
        "urls_created": len(urls),
        "events_created": len(urls),
    }), 201
