"""URL creation with collision handling, validation, and API key authentication.

Features:
- Hash-based short code generation with collision handling
- Idempotent creation (same URL + user = same short code)
- URL validation with SSRF protection
- API key authentication
"""

import hashlib
import random
import string
from datetime import datetime
import json

from flask import Blueprint, jsonify, request, g

from app.cache import cache_delete_url
from app.models.user import User
from app.models.url import Url
from app.models.event import Event
from app.validation import require_api_key, validate_url_decorator

url_creation_bp = Blueprint("url_creation", __name__)

# Base62 characters for short code encoding
BASE62_CHARS = string.ascii_letters + string.digits

# Maximum collision retries before falling back to random
MAX_COLLISION_RETRIES = 10


def _base62_encode(num, length=6):
    """Encode a number to base62 string of specified length."""
    if num == 0:
        return BASE62_CHARS[0] * length

    result = []
    while num > 0:
        result.append(BASE62_CHARS[num % 62])
        num //= 62

    # Pad to desired length
    while len(result) < length:
        result.append(BASE62_CHARS[0])

    return ''.join(reversed(result[-length:]))


def _generate_hash_based_code(original_url, user_id, salt=0):
    """Generate a short code using hash of URL, user, and salt.

    Args:
        original_url: The URL to shorten
        user_id: The user's ID
        salt: Salt value for collision handling

    Returns:
        6-character base62 short code
    """
    # Create deterministic hash from user:url:salt
    hash_input = f"{user_id}:{original_url}:{salt}"
    hash_bytes = hashlib.sha256(hash_input.encode()).digest()

    # Take first 8 bytes and convert to integer
    num = int.from_bytes(hash_bytes[:8], byteorder='big')

    return _base62_encode(num, length=6)


def generate_short_code(length=6):
    """Generate a random short code (fallback method)."""
    characters = string.ascii_letters + string.digits
    while True:
        code = ''.join(random.choices(characters, k=length))
        # Make sure it doesn't already exist
        if not Url.select().where(Url.short_code == code).exists():
            return code


def generate_short_code_with_collision_handling(original_url, user_id):
    """Generate a short code with collision handling and idempotency.

    Algorithm:
    1. Check if (original_url, user_id) already exists -> return existing code
    2. Generate hash-based code from sha256(user_id:original_url:salt)
    3. On collision with DIFFERENT URL: increment salt and retry (max 10)
    4. Fallback to random generation if hash collisions exceed limit

    Args:
        original_url: The URL to shorten
        user_id: The user's ID (or User object)

    Returns:
        tuple: (short_code, existing_url_or_none)
            - If existing URL found: (existing_code, existing_url_object)
            - If new code generated: (new_code, None)
    """
    # Handle User object vs ID
    uid = user_id.id if hasattr(user_id, 'id') else user_id

    # Check for existing URL with same (original_url, user_id) - idempotency
    try:
        existing = Url.get(
            (Url.original_url == original_url) &
            (Url.user_id == uid)
        )
        return existing.short_code, existing
    except Url.DoesNotExist:
        pass

    # Try hash-based generation with collision handling
    for salt in range(MAX_COLLISION_RETRIES):
        code = _generate_hash_based_code(original_url, uid, salt)

        # Check if code exists
        try:
            existing_url = Url.get(Url.short_code == code)

            # Collision with same URL from same user (shouldn't happen, but handle it)
            if existing_url.original_url == original_url and existing_url.user_id_id == uid:
                return code, existing_url

            # Collision with different URL - try next salt
            continue

        except Url.DoesNotExist:
            # Code is available
            return code, None

    # Fallback to random generation if too many hash collisions
    return generate_short_code(), None


@url_creation_bp.route("/shorten", methods=["POST"])
@require_api_key
@validate_url_decorator
def shorten_url():
    """
    Create a shortened URL.

    Headers:
        - X-API-Key: Required API key for authentication

    Request body:
        - original_url: The URL to shorten (validated for SSRF)
        - title: A title/description for the URL

    Returns:
        - short_code: The generated short code
        - short_url: The full shortened URL
        - original_url: The original URL
        - title: The provided title
        - was_existing: True if returning an existing URL (idempotent)
    """
    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error="Request body is required"), 400
    if not isinstance(data, dict):
        return jsonify(error="Request body must be a JSON object"), 400

    # User is set by @require_api_key decorator
    user = g.authenticated_user

    original_url = data.get("original_url")
    title = data.get("title")

    # Validate title (original_url already validated by decorator)
    if not title:
        return jsonify(error="title is required"), 400

    # Generate short code with collision handling and idempotency check
    short_code, existing_url = generate_short_code_with_collision_handling(
        original_url, user
    )

    # If URL already exists for this user, return it (idempotent)
    if existing_url:
        short_url = f"{request.host_url}s/{short_code}"
        redirect_url = f"{request.host_url}urls/{short_code}/redirect"
        return jsonify({
            "id": existing_url.id,
            "short_code": short_code,
            "short_url": short_url,
            "redirect_url": redirect_url,
            "original_url": existing_url.original_url,
            "title": existing_url.title,
            "created_at": existing_url.created_at.isoformat(),
            "was_existing": True
        }), 200

    # Create new URL
    now = datetime.now()
    url = Url.create(
        user_id=user,
        short_code=short_code,
        original_url=original_url,
        title=title,
        is_active=True,
        created_at=now,
        updated_at=now
    )

    # Log the creation event
    Event.create(
        url_id=url,
        user_id=user,
        event_type="created",
        timestamp=now,
        details=json.dumps({
            "short_code": short_code,
            "original_url": original_url
        })
    )

    # Invalidate only this URL's cache (if it somehow existed)
    cache_delete_url(short_code)

    # Build the shortened URL
    short_url = f"{request.host_url}s/{short_code}"
    redirect_url = f"{request.host_url}urls/{short_code}/redirect"

    return jsonify({
        "id": url.id,
        "short_code": short_code,
        "short_url": short_url,
        "redirect_url": redirect_url,
        "original_url": original_url,
        "title": title,
        "created_at": url.created_at.isoformat(),
        "was_existing": False
    }), 201
