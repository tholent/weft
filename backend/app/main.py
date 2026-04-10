# Copyright 2026 Chris Wells <chris@tholent.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.rate_limit import limiter
from app.routers import (
    attachments,
    auth,
    circles,
    export,
    members,
    notifications,
    replies,
    sms_webhook,
    topics,
    transfer,
    updates,
)
from app.scheduler.jobs import shutdown_scheduler, start_scheduler
from app.services.notifications.registry import create_registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.notification_registry = create_registry(settings)
    scheduler = await start_scheduler()
    yield
    await shutdown_scheduler(scheduler)


app = FastAPI(title="Weft", version="0.2.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
app.include_router(notifications.router)
app.include_router(attachments.router)
app.include_router(export.router)
app.include_router(sms_webhook.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
