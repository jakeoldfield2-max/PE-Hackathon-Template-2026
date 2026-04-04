"""URL redirect with analytics and cache management.

Features:
- Click tracking via Redis pub/sub (non-blocking)
- Stats endpoint for click counts
- Cache purging for inactive URLs
"""

from flask import Blueprint, redirect, jsonify, request

from app.cache import cache_get_and_refresh, cache_set, cache_delete
from app.models.url import Url
from app.analytics import publish_click_event, get_click_count

url_redirect_bp = Blueprint("url_redirect", __name__)

# Sliding window TTL - cache expires after this many seconds of inactivity
CACHE_TTL_SECONDS = 5


def _get_url_from_cache_or_db(short_code):
    """
    Fetch URL data from cache or database using sliding window cache.

    How it works:
    1. First request: Cache MISS → fetch from DB → cache with 5s TTL
    2. Request within 5s: Cache HIT → return data → reset TTL to 5s
    3. No requests for 5s: Cache expires → memory released

    This efficiently handles bursts of traffic to the same URL while
    automatically cleaning up when traffic stops.

    Also handles stale inactive URLs by purging them from cache.
    """
    cache_key = f"url:resolve:{short_code}"

    # Check cache first (and refresh TTL if found)
    cached = cache_get_and_refresh(cache_key, ttl=CACHE_TTL_SECONDS)
    if cached is not None:
        # Purge stale inactive URLs from cache
        if not cached.get("is_active", True):
            cache_delete(cache_key)
            # Still return the data, but from "fresh" perspective
            return cached, False
        return cached, True  # (data, is_cached)

    # Fetch from database
    try:
        url = Url.get(Url.short_code == short_code)
        data = {
            "short_code": url.short_code,
            "original_url": url.original_url,
            "title": url.title,
            "is_active": url.is_active,
            "created_at": url.created_at.isoformat(),
            "updated_at": url.updated_at.isoformat(),
        }
        # Only cache if active (don't cache inactive URLs)
        if url.is_active:
            cache_set(cache_key, data, ttl=CACHE_TTL_SECONDS)
        return data, False  # (data, is_cached)
    except Url.DoesNotExist:
        return None, False


def _extract_click_metadata():
    """Extract metadata from request for click tracking."""
    return {
        "ip": request.remote_addr,
        "user_agent": request.headers.get("User-Agent", ""),
        "referer": request.headers.get("Referer", ""),
    }


@url_redirect_bp.route("/s/<short_code>", methods=["GET"])
def redirect_to_original(short_code):
    """
    Redirect a short URL to its original URL.

    Path parameter:
        - short_code: The unique short code for the URL

    Returns:
        - 302 Redirect to the original URL if found and active
        - 404 if short_code not found
        - 410 if URL exists but is inactive
    """
    data, _ = _get_url_from_cache_or_db(short_code)

    if data is None:
        return jsonify(error="Short URL not found", short_code=short_code), 404

    if not data["is_active"]:
        return jsonify(error="This URL has been deactivated", short_code=short_code), 410

    # Track click event (non-blocking)
    metadata = _extract_click_metadata()
    publish_click_event(short_code, metadata)

    return redirect(data["original_url"], code=302)


@url_redirect_bp.route("/s/<short_code>/info", methods=["GET"])
def get_url_info(short_code):
    """
    Get information about a short URL without redirecting.

    Path parameter:
        - short_code: The unique short code for the URL

    Returns:
        - URL details (original_url, title, created_at, etc.)
        - 404 if short_code not found
    """
    data, is_cached = _get_url_from_cache_or_db(short_code)

    if data is None:
        return jsonify(error="Short URL not found", short_code=short_code), 404

    headers = {"X-Cache": "HIT" if is_cached else "MISS"}
    return jsonify(data), 200, headers


@url_redirect_bp.route("/s/<short_code>/stats", methods=["GET"])
def get_url_stats(short_code):
    """
    Get click statistics for a short URL.

    Path parameter:
        - short_code: The unique short code for the URL

    Returns:
        - short_code: The short code
        - click_count: Total number of clicks
        - 404 if short_code not found
    """
    # Verify URL exists
    data, _ = _get_url_from_cache_or_db(short_code)

    if data is None:
        return jsonify(error="Short URL not found", short_code=short_code), 404

    click_count = get_click_count(short_code)

    return jsonify({
        "short_code": short_code,
        "click_count": click_count
    }), 200
