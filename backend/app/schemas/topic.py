import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import TopicStatus


class TopicCreate(BaseModel):
    default_title: str
    creator_email: str | None = None


class TopicResponse(BaseModel):
    id: uuid.UUID
    default_title: str
    status: TopicStatus
    created_at: datetime
    closed_at: datetime | None = None
    scoped_title: str | None = None


class TopicCreateResponse(BaseModel):
    topic: TopicResponse
    token: str
    magic_link: str
