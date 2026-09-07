# backend/app/core/redis.py
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)
redis_client = None

try:
    import redis.asyncio as redis

    async def init_redis():
        global redis_client

        if not settings.REDIS_URL:
            logger.warning("⚠️ REDIS_URL not configured - Redis features disabled")
            redis_client = None
            return None

        try:
            redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await redis_client.ping()
            logger.info("✅ Redis connected successfully")
            return redis_client
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {str(e)}")
            redis_client = None
            return None

    async def close_redis():
        global redis_client
        if redis_client:
            await redis_client.aclose()
            redis_client = None
            logger.info("✅ Redis connection closed")

except ImportError:
    logger.warning("⚠️ redis.asyncio not available - Redis features disabled")

    async def init_redis():
        return None

    async def close_redis():
        pass
