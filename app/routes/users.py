import csv
from io import StringIO
from datetime import datetime
from contextlib import contextmanager

from flask import Blueprint, jsonify, request
from peewee import IntegrityError
from playhouse.shortcuts import model_to_dict

from app.database import db
from app.cache import cache_get, cache_set, cache_delete_pattern, cache_delete_url
from app.models.event import Event
from app.models.url import Url
from app.models.user import User

users_bp = Blueprint("users", __name__)


@contextmanager
def _db_context():
    database = getattr(db, "obj", None)
    if getattr(database, "database", None) == ":memory:":
        yield
    else:
        with db.connection_context():
            yield


def _serialize_user(user):
    data = model_to_dict(user, recurse=False)
    for key in ("created_at",):
        value = data.get(key)
        if hasattr(value, "isoformat"):
            data[key] = value.isoformat()
    return data


def _parse_int(value, default=None):
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _get_list_params():
    payload = request.get_json(silent=True) or {}

    page = request.args.get("page", type=int)
    if page is None:
        page = _parse_int(payload.get("page"), 1)
    if page is None or page < 1:
        page = 1

    per_page = request.args.get("per_page", type=int)
    if per_page is None:
        per_page = _parse_int(payload.get("per_page"), 50)
    if per_page is None or per_page < 1:
        per_page = 50
    per_page = min(per_page, 100)

    limit = request.args.get("limit", type=int)
    if limit is None and payload.get("limit") is not None:
        limit = _parse_int(payload.get("limit"))
    if limit is not None and limit < 1:
        limit = None
    if limit is not None:
        limit = min(limit, 100)

    offset = request.args.get("offset", type=int)
    if offset is None and payload.get("offset") is not None:
        offset = _parse_int(payload.get("offset"), 0)
    if offset is None or offset < 0:
        offset = 0

    return page, per_page, limit, offset


@users_bp.route("/users", methods=["POST"])
def create_user():
    """Create a new user with username and email."""
    data = request.get_json()

    if not data:
        return jsonify(error="Request body is required"), 400

    username = data.get("username")
    email = data.get("email")

    if not username or not email:
        return jsonify(error="username and email are required"), 400

    with _db_context():
        if User.select().where(User.username == username).exists():
            return jsonify(error="Username already exists"), 409

        if User.select().where(User.email == email).exists():
            return jsonify(error="Email already exists"), 409

        try:
            user = User.create(
                username=username,
                email=email,
                created_at=datetime.now()
            )
        except IntegrityError:
            # Race condition: another request created the same user between check and insert
            return jsonify(error="Username or email already exists"), 409

    cache_delete_pattern("users:*")

    return jsonify(_serialize_user(user)), 201


@users_bp.route("/users/bulk", methods=["POST"])
def bulk_create_users():
    """Create users from an uploaded CSV file."""
    upload = request.files.get("file")
    payload = request.get_json(silent=True) or {}
    expected_row_count = request.form.get("row_count", type=int)
    if expected_row_count is None:
        expected_row_count = payload.get("row_count")

    csv_text = None
    if upload is not None:
        csv_text = upload.read().decode("utf-8-sig")
    elif isinstance(payload.get("csv"), str):
        csv_text = payload["csv"]

    if not csv_text:
        return jsonify(error="CSV file is required"), 400

    rows = list(csv.DictReader(StringIO(csv_text)))
    if expected_row_count is not None and expected_row_count != len(rows):
        return jsonify(error="row_count does not match CSV rows"), 400

    created_users = []
    skipped_rows = 0

    with _db_context(), db.atomic():
        for row in rows:
            username = (row.get("username") or "").strip()
            email = (row.get("email") or "").strip()

            if not username or not email:
                skipped_rows += 1
                continue

            if User.select().where((User.username == username) | (User.email == email)).exists():
                skipped_rows += 1
                continue

            user = User.create(
                username=username,
                email=email,
                created_at=datetime.now(),
            )
            created_users.append(_serialize_user(user))

    cache_delete_pattern("users:*")

    status_code = 201 if created_users else 200
    return jsonify({
        "message": "Bulk user import complete",
        "created": len(created_users),
        "skipped": skipped_rows,
        "row_count": len(rows),
        "users": created_users,
    }), status_code


@users_bp.route("/users", methods=["GET"])
def list_users():
    """List all users with pagination."""
    page, per_page, limit, offset = _get_list_params()

    if limit is None:
        limit = per_page
        offset = (page - 1) * per_page + offset

    cache_key = f"users:list:{limit}:{offset}"
    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify(cached), 200, {"X-Cache": "HIT"}

    with _db_context():
        total = User.select().count()
        users = User.select().order_by(User.id).limit(limit).offset(offset)
        users_list = [_serialize_user(u) for u in users]

    result = {
        "users": users_list,
        "pagination": {
            "page": page,
            "per_page": limit,
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_more": offset + len(users_list) < total,
        }
    }
    cache_set(cache_key, result, ttl=10)

    return jsonify(result), 200, {"X-Cache": "MISS"}


@users_bp.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    """Get a specific user by ID."""
    cached = cache_get(f"users:{user_id}")
    if cached is not None:
        return jsonify(cached), 200, {"X-Cache": "HIT"}

    with _db_context():
        try:
            user = User.get_by_id(user_id)
            result = _serialize_user(user)
            cache_set(f"users:{user_id}", result, ttl=10)
            return jsonify(result), 200, {"X-Cache": "MISS"}
        except User.DoesNotExist:
            return jsonify(error="User not found"), 404


@users_bp.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    """Update a user's username or email."""
    data = request.get_json(silent=True) or {}
    updates = {key: value for key, value in data.items() if key in {"username", "email"}}
    if not updates:
        return jsonify(error="No valid fields provided"), 400

    with _db_context():
        try:
            user = User.get_by_id(user_id)
        except User.DoesNotExist:
            return jsonify(error="User not found"), 404

        if "username" in updates:
            if User.select().where((User.username == updates["username"]) & (User.id != user_id)).exists():
                return jsonify(error="Username already exists"), 409
            user.username = updates["username"]

        if "email" in updates:
            if User.select().where((User.email == updates["email"]) & (User.id != user_id)).exists():
                return jsonify(error="Email already exists"), 409
            user.email = updates["email"]

        user.save()

    cache_delete_pattern("users:list:*")
    cache_delete_pattern(f"users:{user_id}")
    return jsonify(_serialize_user(user)), 200


@users_bp.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    """Delete a user and their related URLs/events."""
    with _db_context(), db.atomic():
        try:
            user = User.get_by_id(user_id)
        except User.DoesNotExist:
            return jsonify(message="User not found", deleted_user_id=user_id), 200

        user_urls = list(Url.select().where(Url.user_id == user_id))
        url_ids = [url.id for url in user_urls]
        short_codes = [url.short_code for url in user_urls]

        if url_ids:
            Event.delete().where(Event.url_id.in_(url_ids)).execute()
            Url.delete().where(Url.id.in_(url_ids)).execute()

        Event.delete().where(Event.user_id == user_id).execute()
        user.delete_instance()

    cache_delete_pattern("users:list:*")
    cache_delete_pattern(f"users:{user_id}")
    for short_code in short_codes:
        cache_delete_url(short_code)

    return jsonify(message="User deleted successfully", deleted_user_id=user_id), 200


@users_bp.route("/users/<int:user_id>/api-key", methods=["POST"])
def generate_api_key(user_id):
    """Generate a new API key for a user.

    This replaces any existing API key for the user.

    Path parameter:
        - user_id: ID of the user to generate key for

    Returns:
        - api_key: The newly generated API key (format: upk_{token})
        - user_id: The user's ID
        - message: Success message
    """
    with _db_context():
        try:
            user = User.get_by_id(user_id)
        except User.DoesNotExist:
            return jsonify(error="User not found"), 404

        # Generate new API key
        new_api_key = User.generate_api_key()

        # Update user with new key
        user.api_key = new_api_key
        user.save()

    # Invalidate user cache
    cache_delete_pattern(f"users:{user_id}")
    cache_delete_pattern("users:list:*")

    return jsonify({
        "api_key": new_api_key,
        "user_id": user_id,
        "message": "API key generated successfully. Store this key securely - it cannot be retrieved later."
    }), 201
