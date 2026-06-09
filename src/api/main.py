from fastapi import FastAPI
from routers.notifications import router as notifications_router
from routers.subscribers import router as subscribers_router

app = FastAPI()

app.include_router(notifications_router, prefix="/notifications")
app.include_router(subscribers_router, prefix="/subscribers")