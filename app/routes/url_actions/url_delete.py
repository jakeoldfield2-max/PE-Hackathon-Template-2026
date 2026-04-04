from datetime import datetime
import json

from flask import Blueprint, jsonify, request

from app.cache import cache_delete_pattern
from app.models.user import User
from app.models.url import Url
from app.models.event import Event

url_delete_bp = Blueprint("url_delete", __name__)


@url_delete_bp.route("/delete", methods=["POST"])
def delete_url():
    """
    Delete a URL by short_code.

    Request body:
        - short_code: The code of the URL to delete

    Returns:
        - Confirmation of deletion
    """
    data = request.get_json()

    if not data:
        return jsonify(error="Request body is required"), 400

    short_code = data.get("short_code")
    if not short_code:
        return jsonify(error="short_code is required"), 400

    # Find the URL by short_code
    try:
        url = Url.get(Url.short_code == short_code)
    except Url.DoesNotExist:
        return jsonify(error="URL not found"), 404

    # Store URL info for response before deletion
    deleted_url_info = {
        "id": url.id,
        "short_code": url.short_code,
        "original_url": url.original_url,
        "title": url.title
    }

    # Delete all events associated with this URL
    events_deleted = Event.delete().where(Event.url_id == url.id).execute()

    # Delete the URL record
    url.delete_instance()

    cache_delete_pattern("urls:*")

    return jsonify({
        "message": "URL deleted successfully",
        "deleted_url": deleted_url_info,
        "events_deleted": events_deleted
    }), 200

