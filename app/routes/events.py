import json
from datetime import datetime

from flask import Blueprint, jsonify, request
from playhouse.shortcuts import model_to_dict

from app.models.event import Event
from app.models.url import Url
from app.models.user import User


events_bp = Blueprint("events", __name__)


def _parse_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_payload(raw):
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        return None
    return raw


def _serialize_event(event):
    data = model_to_dict(event, recurse=False)

    url_value = data.get("url_id")
    user_value = data.get("user_id")
    if isinstance(url_value, dict):
        data["url_id"] = url_value.get("id")
    if isinstance(user_value, dict):
        data["user_id"] = user_value.get("id")

    if hasattr(data.get("timestamp"), "isoformat"):
        data["timestamp"] = data["timestamp"].isoformat()

    details = data.get("details")
    if isinstance(details, str):
        try:
            data["details"] = json.loads(details)
        except (TypeError, ValueError):
            pass

    return data


@events_bp.route("/events", methods=["GET"])
def list_events():
    payload = _normalize_payload(request.get_json(silent=True))
    if payload is None:
        return jsonify(error="Request body must be a JSON object"), 400

    url_id = request.args.get("url_id", type=int)
    if url_id is None and "url_id" in payload:
        url_id = _parse_int(payload.get("url_id"))

    user_id = request.args.get("user_id", type=int)
    if user_id is None and "user_id" in payload:
        user_id = _parse_int(payload.get("user_id"))

    event_type = request.args.get("event_type")
    if not event_type and "event_type" in payload:
        event_type = payload.get("event_type")

    query = Event.select().order_by(Event.id)
    if url_id is not None:
        query = query.where(Event.url_id == url_id)
    if user_id is not None:
        query = query.where(Event.user_id == user_id)
    if event_type:
        query = query.where(Event.event_type == str(event_type).strip())

    return jsonify([_serialize_event(event) for event in query]), 200


@events_bp.route("/events", methods=["POST"])
def create_event():
    payload = _normalize_payload(request.get_json(silent=True))
    if payload is None:
        return jsonify(error="Request body must be a JSON object"), 400

    if not payload:
        return jsonify(error="Request body is required"), 400

    url_id = _parse_int(payload.get("url_id"))
    user_id = _parse_int(payload.get("user_id"))
    event_type = payload.get("event_type")
    details = payload.get("details")

    if url_id is None:
        return jsonify(error="url_id is required"), 400
    if user_id is None:
        return jsonify(error="user_id is required"), 400
    if not event_type:
        return jsonify(error="event_type is required"), 400

    try:
        url = Url.get_by_id(url_id)
    except Url.DoesNotExist:
        return jsonify(error="URL not found"), 404

    try:
        user = User.get_by_id(user_id)
    except User.DoesNotExist:
        return jsonify(error="User not found"), 404

    event = Event.create(
        url_id=url,
        user_id=user,
        event_type=str(event_type).strip(),
        timestamp=datetime.now(),
        details=json.dumps(details if details is not None else {}),
    )

    return jsonify(_serialize_event(event)), 201
