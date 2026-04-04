"""Redis caching layer with TTL and cache invalidation.

WHY: Under 500 concurrent users, the DB becomes the bottleneck.
Redis caching with ~10s TTL achieves ~91% cache hit rate, reducing
DB load dramatically. Without this, tsunami load test fails.
Reference: CAPACITY.md bottleneck analysis, tsunami.js cache assertions.
"""

import json
import os
import logging
from redis import ConnectionPool

logger = logging.getLogger(__name__)

_redis_pool = None
_redis_client = None


def _get_redis_pool():
    """Initialize and return the Redis connection pool."""
    global _redis_pool
    if _redis_pool is not None:
        return _redis_pool

    try:
        host = os.environ.get("REDIS_HOST", "localhost")
        port = int(os.environ.get("REDIS_PORT", 6379))

        _redis_pool = ConnectionPool(
            host=host,
            port=port,
            db=0,
            max_connections=50,
            socket_timeout=30,
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=30,
            decode_responses=True
        )
        logger.info("Redis connection pool initialized at %s:%s", host, port)
        return _redis_pool
    except Exception as e:
        logger.warning("Failed to initialize Redis pool: %s", e)
        return None


def get_redis():
    """Get a Redis client from the pool. Returns None if Redis unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    try:
        import redis
        pool = _get_redis_pool()
        if pool is None:
            return None

        _redis_client = redis.Redis(connection_pool=pool)
        _redis_client.ping()
        logger.info("Redis client connected via connection pool")
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


def cache_get_and_refresh(key, ttl=5):
    """Get a cached value and refresh its TTL (sliding window cache).

    This extends the cache lifetime on each access. If no requests come
    within the TTL period, the cache expires and releases the memory.

    Args:
        key: The cache key to fetch
        ttl: Time-to-live in seconds to reset on each hit (default: 5s)

    Returns:
        The cached value, or None on miss or Redis unavailable.
    """
    r = get_redis()
    if r is None:
        return None
    try:
        val = r.get(key)
        if val is not None:
            # Refresh TTL on hit - extends the sliding window
            r.expire(key, ttl)
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


def cache_delete(key):
    """Delete a specific cache key.

    Args:
        key: The exact cache key to delete
    """
    r = get_redis()
    if r is None:
        return
    try:
        r.delete(key)
    except Exception:
        pass


def cache_delete_url(short_code):
    """Delete all cache entries for a specific short URL.

    Removes:
    - url:resolve:{short_code} - The URL resolution cache
    - clicks:{short_code} - The click count cache

    Args:
        short_code: The short code of the URL to invalidate
    """
    r = get_redis()
    if r is None:
        return
    try:
        r.delete(
            f"url:resolve:{short_code}",
            f"clicks:{short_code}"
        )
    except Exception:
        pass
