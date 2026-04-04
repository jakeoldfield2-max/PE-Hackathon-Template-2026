from flask import Blueprint, jsonify, request
from playhouse.shortcuts import model_to_dict

from app.cache import cache_get, cache_set
from app.models.url import Url

urls_bp = Blueprint("urls", __name__)


@urls_bp.route("/urls", methods=["GET"])
def list_urls():
    """List URLs with pagination for dashboard/table views."""
    limit = request.args.get("limit", default=100, type=int)
    offset = request.args.get("offset", default=0, type=int)

    limit = min(limit, 200)

    cache_key = f"urls:list:{limit}:{offset}"
    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify(cached), 200, {"X-Cache": "HIT"}

    total = Url.select().count()
    urls = Url.select().order_by(Url.created_at.desc()).limit(limit).offset(offset)
    urls_list = [model_to_dict(u, recurse=False) for u in urls]

    result = {
        "urls": urls_list,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_more": offset + len(urls_list) < total,
        },
    }

    cache_set(cache_key, result, ttl=10)
    return jsonify(result), 200, {"X-Cache": "MISS"}
