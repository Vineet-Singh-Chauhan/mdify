"""Stats tracker using local persistent Redis database.

All stats are stored in the local Redis server and persist forever
across restarts since no TTL is applied.
"""
import logging
from src.IngestionContext.tracker import get_redis as get_local_redis

logger = logging.getLogger(__name__)

def increment_visitors() -> int:
    """Increment visitor counter in local persistent Redis."""
    try:
        local = get_local_redis()
        val = local.incr("mdify:stats:visitors")
        logger.info("[stats] Local visitors incremented: %d", val)
        return int(val)
    except Exception as exc:
        logger.warning("[stats] Failed to increment visitors: %s", exc)
        return 0

def increment_conversions() -> int:
    """Increment PDF conversion counter in local persistent Redis."""
    try:
        local = get_local_redis()
        val = local.incr("mdify:stats:conversions")
        logger.info("[stats] Local conversions incremented: %d", val)
        return int(val)
    except Exception as exc:
        logger.warning("[stats] Failed to increment conversions: %s", exc)
        return 0

def get_stats() -> dict[str, int]:
    """Retrieve visitors and conversions stats from local persistent Redis."""
    try:
        local = get_local_redis()
        visitors = local.get("mdify:stats:visitors")
        conversions = local.get("mdify:stats:conversions")
        return {
            "visitors": int(visitors) if visitors is not None else 0,
            "conversions": int(conversions) if conversions is not None else 0,
        }
    except Exception as exc:
        logger.warning("[stats] Failed to retrieve stats: %s", exc)
        return {"visitors": 0, "conversions": 0}
