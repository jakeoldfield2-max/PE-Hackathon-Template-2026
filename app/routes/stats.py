from flask import Blueprint, jsonify
from peewee import fn

from app.observability import update_business_metrics
from app.models.user import User
from app.models.url import Url
from app.models.event import Event

stats_bp = Blueprint("stats", __name__)


@stats_bp.route("/stats")
def stats():
    """System overview metrics.
    WHY: Provides a quick summary for Grafana dashboard business metrics
    panels and the demo video. Reference: FEATURES.md observability evidence.
    """
    total_users = User.select().count()
    total_urls = Url.select().count()
    active_urls = Url.select().where(Url.is_active == True).count()  # noqa: E712
    active_users = (
        Url.select(Url.user_id)
        .where(Url.is_active == True)  # noqa: E712
        .distinct()
        .count()
    )
    total_events = Event.select().count()

    update_business_metrics(active_urls=active_urls, active_users=active_users)

    event_breakdown = {}
    for row in (
        Event.select(Event.event_type, fn.COUNT(Event.id).alias("count"))
        .group_by(Event.event_type)
    ):
        event_breakdown[row.event_type] = row.count

    return jsonify({
        "total_users": total_users,
        "total_urls": total_urls,
        "active_urls": active_urls,
        "active_users": active_users,
        "total_events": total_events,
        "events_by_type": event_breakdown,
    })
