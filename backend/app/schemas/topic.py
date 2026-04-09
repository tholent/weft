import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import TopicStatus


class TopicCreate(BaseModel):
    default_title: str = Field(min_length=1, max_length=200)
    creator_email: EmailStr | None = None


class TopicResponse(BaseModel):
    id: uuid.UUID
    default_title: str
    status: TopicStatus
    created_at: datetime
    closed_at: datetime | None = None
    scoped_title: str | None = None


class TopicCreateResponse(BaseModel):
    topic: TopicResponse
    magic_link: str
