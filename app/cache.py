"""Redis caching layer with TTL and cache invalidation.

WHY: Under 500 concurrent users, the DB becomes the bottleneck.
Redis caching with ~10s TTL achieves ~91% cache hit rate, reducing
DB load dramatically. Without this, tsunami load test fails.
Reference: CAPACITY.md bottleneck analysis, tsunami.js cache assertions.
"""

import json
import os
import logging

logger = logging.getLogger(__name__)

_redis_client = None


def get_redis():
    """Lazy-init Redis connection. Returns None if Redis unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    try:
        import redis
        host = os.environ.get("REDIS_HOST", "localhost")
        port = int(os.environ.get("REDIS_PORT", 6379))
        _redis_client = redis.Redis(host=host, port=port, decode_responses=True)
        _redis_client.ping()
        logger.info("Redis connected at %s:%s", host, port)
        return _redis_client
    except Exception:
        # WHY graceful degradation: If Redis is down, app still works
        # but without caching. This is documented in FAILURE_MODES.md
        # scenario 3 — "Redis down: app still works, just slower."
        logger.warning("Redis unavailable — caching disabled")
        _redis_client = None
        return None


def cache_get(key):
    """Get a cached value. Returns None on miss or Redis unavailable."""
    r = get_redis()
    if r is None:
        return None
    try:
        val = r.get(key)
        if val is not None:
            return json.loads(val)
    except Exception:
        pass
    return None


def cache_set(key, value, ttl=10):
    """Set a cache value with TTL in seconds."""
    r = get_redis()
    if r is None:
        return
    try:
        r.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


def cache_delete_pattern(pattern):
    """Delete all keys matching a pattern. Used for cache invalidation."""
    r = get_redis()
    if r is None:
        return
    try:
        keys = r.keys(pattern)
        if keys:
            r.delete(*keys)
    except Exception:
        pass
