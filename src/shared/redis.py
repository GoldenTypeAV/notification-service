import redis.asyncio as redis
from src.shared.settings import settings

redis_client: redis.Redis | None = None

async def init_redis():
    global redis_client
    redis_client = await redis.from_url(str(settings.redis.url), decode_responses=True)

async def close_redis():
    if redis_client:
        await redis_client.close()

async def get_redis() -> redis.Redis:
    return redis_client