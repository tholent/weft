from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, circles, members, replies, topics, transfer, updates
from app.scheduler.jobs import shutdown_scheduler, start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = await start_scheduler()
    yield
    await shutdown_scheduler(scheduler)


app = FastAPI(title="Weft", version="0.1.0", lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(topics.router)
app.include_router(circles.router)
app.include_router(members.router)
app.include_router(updates.router)
app.include_router(replies.router)
app.include_router(transfer.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
