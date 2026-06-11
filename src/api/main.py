from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.api.v1.routers.admin import router as admin_router
from src.api.v1.routers.notifications import router as notifications_router
from src.api.v1.routers.subscribers import router as subscribers_router
from src.shared.redis import init_redis, close_redis
from src.shared.kafka import init_kafka_producer, close_kafka_producer
from src.shared.database import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    await init_kafka_producer()
    
    yield
    
    await close_kafka_producer()
    await close_redis()
    await engine.dispose()

app = FastAPI(
    title="Notification Service",
    lifespan=lifespan
)

api_v1_prefix = "/api/v1"
app.include_router(admin_router, prefix=api_v1_prefix)
app.include_router(notifications_router, prefix=api_v1_prefix)
app.include_router(subscribers_router, prefix=api_v1_prefix)