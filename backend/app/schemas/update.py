import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UpdateCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)
    circle_ids: list[uuid.UUID] = Field(min_length=1)


class UpdateEdit(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


class UpdateResponse(BaseModel):
    id: uuid.UUID
    body: str
    author_member_id: uuid.UUID
    author_handle: str | None = None
    circle_ids: list[uuid.UUID] = []
    created_at: datetime
    edited_at: datetime | None = None
    deleted_at: datetime | None = None
    reply_count: int = 0
