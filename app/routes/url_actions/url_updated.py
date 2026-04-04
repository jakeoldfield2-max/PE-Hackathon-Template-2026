from datetime import datetime
import json

from flask import Blueprint, jsonify, request

from app.cache import cache_delete_pattern
from app.models.user import User
from app.models.url import Url
from app.models.event import Event

url_updated_bp = Blueprint("url_updated", __name__)

# Fields that are allowed to be updated
ALLOWED_FIELDS = ["title", "is_active", "original_url"]


@url_updated_bp.route("/update", methods=["POST"])
def update_url():
    """
    Update a specific field of a URL.

    Request body:
        - short_code: The code of the URL to update
        - title: Optional new title
        - is_active: Optional new active status
        - original_url: Optional new destination URL

    Returns:
        - Confirmation with updated URL details
    """
    data = request.get_json()

    if not data:
        return jsonify(error="Request body is required"), 400

    short_code = data.get("short_code")
    if not short_code:
        return jsonify(error="short_code is required"), 400

    # Verify URL exists
    try:
        url = Url.get(Url.short_code == short_code)
    except Url.DoesNotExist:
        return jsonify(error="URL not found"), 404

    # Track changes for event logging
    changes = {}
    for field in ALLOWED_FIELDS:
        if field in data:
            new_value = data[field]
            old_value = getattr(url, field)
            if new_value != old_value:
                setattr(url, field, new_value)
                changes[field] = {"old": str(old_value), "new": str(new_value)}

    if changes:
        url.updated_at = datetime.now()
        url.save()
        cache_delete_pattern("urls:*")

        # Log the update event (use a system or generic user if user_id not provided)
        user_id = data.get("user_id") or url.user_id_id
        Event.create(
            url_id=url,
            user_id=user_id,
            event_type="updated",
            timestamp=datetime.now(),
            details=json.dumps(changes)
        )

    return jsonify({
        "message": "URL updated successfully",
        "short_code": short_code,
        "changes": changes,
        "updated_at": url.updated_at.isoformat()
    }), 200

