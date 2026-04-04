from datetime import datetime

from flask import Blueprint, jsonify, request
from peewee import IntegrityError
from playhouse.shortcuts import model_to_dict

from app.cache import cache_get, cache_set, cache_delete_pattern
from app.models.user import User

users_bp = Blueprint("users", __name__)


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

    return jsonify(model_to_dict(user)), 201


@users_bp.route("/users", methods=["GET"])
def list_users():
    """List all users with pagination."""
    # Parse pagination parameters
    limit = request.args.get("limit", default=50, type=int)
    offset = request.args.get("offset", default=0, type=int)

    # Enforce max limit
    limit = min(limit, 100)

    cache_key = f"users:list:{limit}:{offset}"
    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify({"users": cached, "limit": limit, "offset": offset}), 200, {"X-Cache": "HIT"}

    # Get total count and paginated users
    total = User.select().count()
    users = User.select().order_by(User.id).limit(limit).offset(offset)
    users_list = [model_to_dict(u) for u in users]

    result = {
        "users": users_list,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_more": offset + len(users_list) < total
        }
    }
    cache_set(cache_key, result, ttl=10)

    return jsonify({"users": result, "limit": limit, "offset": offset}), 200, {"X-Cache": "MISS"}


@users_bp.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    """Get a specific user by ID."""
    cached = cache_get(f"users:{user_id}")
    if cached is not None:
        return jsonify(cached), 200, {"X-Cache": "HIT"}

    try:
        user = User.get_by_id(user_id)
        result = model_to_dict(user)
        cache_set(f"users:{user_id}", result, ttl=10)
        return jsonify(result), 200, {"X-Cache": "MISS"}
    except User.DoesNotExist:
        return jsonify(error="User not found"), 404
