import redis.asyncio as redis
from src.shared.settings import settings

redis_client: redis.Redis | None = None


async def init_redis() -> redis.Redis:
    global redis_client
    redis_client = await redis.from_url(str(settings.redis.url), decode_responses=True)
    return redis_client


async def close_redis() -> None:
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


async def get_redis() -> redis.Redis:
    return redis_client


def history_cache_key(subscriber_id: int) -> str:
    return f"history:{subscriber_id}"


async def invalidate_history(client: redis.Redis, subscriber_id: int) -> None:
    if client is not None:
        await client.delete(history_cache_key(subscriber_id))


def idempotency_lock_name(key: str) -> str:
    return f"idem:{key}"


async def claim_idempotency(client: redis.Redis, key: str, ttl: int) -> bool:
    """True, если ключ был свободен (новое сообщение)."""
    acquired = await client.set(idempotency_lock_name(key), "1", nx=True, ex=ttl)
    return bool(acquired)


def processing_lock_name(notification_id: int) -> str:
    return f"lock:notif:{notification_id}"


async def acquire_processing_lock(client: redis.Redis, notification_id: int, ttl: int) -> bool:
    acquired = await client.set(processing_lock_name(notification_id), "1", nx=True, ex=ttl)
    return bool(acquired)


async def release_processing_lock(client: redis.Redis, notification_id: int) -> None:
    if client is not None:
        await client.delete(processing_lock_name(notification_id))
