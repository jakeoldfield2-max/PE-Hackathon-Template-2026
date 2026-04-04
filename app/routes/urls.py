from flask import Blueprint, jsonify, request
from playhouse.shortcuts import model_to_dict

from app.cache import cache_get, cache_set
from app.models.url import Url
from app.models.user import User

urls_bp = Blueprint("urls", __name__)

@urls_bp.route("/urls", methods=["GET"])
def list_urls():
    """List shortened URLs (paginated for production)."""
    limit = request.args.get("limit", default=100, type=int)
    offset = request.args.get("offset", default=0, type=int)
    
    # Cap limit to prevent massive database queries
    limit = min(limit, 500)

    cache_key = f"urls:list:{limit}:{offset}"
    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify({"urls": cached, "limit": limit, "offset": offset}), 200, {"X-Cache": "HIT"}

    # Use JOIN to prevent N+1 queries when fetching the associated User
    urls = Url.select(Url, User).join(User).order_by(Url.id.desc()).limit(limit).offset(offset)
    
    # model_to_dict recursively serializes the User object as well because we JOINed it
    result = [model_to_dict(u) for u in urls]
    
    # Cache for a short duration
    cache_set(cache_key, result, ttl=5)

    return jsonify({"urls": result, "limit": limit, "offset": offset}), 200, {"X-Cache": "MISS"}

