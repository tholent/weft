import uuid
from datetime import datetime

from pydantic import BaseModel


class UpdateCreate(BaseModel):
    body: str
    circle_ids: list[uuid.UUID]


class UpdateEdit(BaseModel):
    body: str


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
