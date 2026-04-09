import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ModResponseScope, RelayStatus


class ReplyCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    wants_to_share: bool = False


class RelayAction(BaseModel):
    circle_ids: list[uuid.UUID] | None = None


class ModResponseCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    scope: ModResponseScope


class ModResponseResponse(BaseModel):
    id: uuid.UUID
    body: str
    author_handle: str | None = None
    scope: ModResponseScope
    created_at: datetime


class ReplyResponse(BaseModel):
    id: uuid.UUID
    body: str
    author_member_id: uuid.UUID
    author_handle: str | None = None
    wants_to_share: bool
    relay_status: RelayStatus
    created_at: datetime
    mod_responses: list[ModResponseResponse] = []
