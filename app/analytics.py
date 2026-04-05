"""Async analytics via Redis pub/sub for click tracking.

This module provides non-blocking click event publishing and fast click counts.
Events are published to Redis pub/sub for optional background processing.

Architecture:
1. publish_click_event() - Non-blocking, called on each URL redirect
   - Increments Redis counter for fast reads
   - Publishes event to pub/sub channel for optional persistence

2. get_click_count() - Fast read from Redis counter

3. start_analytics_subscriber() - Optional background worker
   - Subscribes to pub/sub channel
   - Persists click events to database Event table
"""

import json
import logging
import threading
from datetime import datetime, timezone

from app.cache import get_redis

logger = logging.getLogger(__name__)

# Redis pub/sub channel for click events
ANALYTICS_CHANNEL = "urlpulse:analytics:clicks"


def publish_click_event(short_code, metadata=None):
    """Publish a click event to Redis (non-blocking).

    This function:
    1. Increments the click counter for fast reads
    2. Publishes event to pub/sub channel for optional persistence

    Args:
        short_code: The short code that was clicked
        metadata: Optional dict with additional info (ip, user_agent, referer, etc.)
    """
    try:
        # Persist click event immediately so tracking works even without subscriber.
        # Import lazily to avoid circular imports at module load.
        from app.models.event import Event
        from app.models.url import Url

        try:
            url = Url.get(Url.short_code == short_code)
            Event.create(
                url_id=url,
                user_id=url.user_id,
                event_type="click",
                timestamp=datetime.now(timezone.utc),
                details=json.dumps(metadata or {}),
            )
        except Url.DoesNotExist:
            logger.warning("Click event for unknown short_code: %s", short_code)

        r = get_redis()
        if r is None:
            logger.debug("Redis unavailable, click counter/pubsub skipped for %s", short_code)
            return

        # Increment click counter (atomic, fast)
        counter_key = f"clicks:{short_code}"
        r.incr(counter_key)

        # Build event payload for pub/sub
        event = {
            "short_code": short_code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }

        # Publish to channel (non-blocking for subscribers)
        r.publish(ANALYTICS_CHANNEL, json.dumps(event))

        logger.debug("Click event published for %s", short_code)
    except Exception as e:
        # Non-blocking: don't let analytics failures affect redirects
        logger.warning("Failed to publish click event for %s: %s", short_code, e)


def get_click_count(short_code):
    """Get the click count for a short URL from Redis.

    Args:
        short_code: The short code to get clicks for

    Returns:
        Integer click count, or 0 if not found or Redis unavailable
    """
    r = get_redis()
    if r is None:
        return 0

    try:
        counter_key = f"clicks:{short_code}"
        count = r.get(counter_key)
        return int(count) if count else 0
    except Exception as e:
        logger.warning("Failed to get click count for %s: %s", short_code, e)
        return 0


def start_analytics_subscriber():
    """Start a background subscriber that persists click events to database.

    This function starts a daemon thread that:
    1. Subscribes to the analytics pub/sub channel
    2. Receives click events as they're published
    3. Persists them to the Event table with event_type="click"

    Call this at application startup if you want database persistence.
    The thread runs as a daemon and will stop when the main process exits.

    Returns:
        The subscriber thread object
    """
    def subscriber_loop():
        # Import here to avoid circular imports
        from app.models.event import Event
        from app.models.url import Url
        from app.models.user import User

        r = get_redis()
        if r is None:
            logger.error("Cannot start analytics subscriber: Redis unavailable")
            return

        pubsub = r.pubsub()
        pubsub.subscribe(ANALYTICS_CHANNEL)

        logger.info("Analytics subscriber started, listening on %s", ANALYTICS_CHANNEL)

        for message in pubsub.listen():
            if message["type"] != "message":
                continue

            try:
                event_data = json.loads(message["data"])
                short_code = event_data.get("short_code")

                if not short_code:
                    continue

                # Find the URL
                try:
                    url = Url.get(Url.short_code == short_code)
                except Url.DoesNotExist:
                    logger.warning("Click event for unknown short_code: %s", short_code)
                    continue

                # Create click event in database
                Event.create(
                    url_id=url,
                    user_id=url.user_id,
                    event_type="click",
                    timestamp=datetime.now(timezone.utc),
                    details=json.dumps(event_data.get("metadata", {}))
                )

                logger.debug("Persisted click event for %s", short_code)

            except json.JSONDecodeError:
                logger.warning("Invalid JSON in analytics event")
            except Exception as e:
                logger.error("Error processing click event: %s", e)

    thread = threading.Thread(target=subscriber_loop, daemon=True)
    thread.start()
    return thread
