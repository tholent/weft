import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import MemberRole


class MemberInvite(BaseModel):
    email: str
    circle_id: uuid.UUID
    role: MemberRole = MemberRole.recipient


class MemberMove(BaseModel):
    new_circle_id: uuid.UUID
    retroactive_revoke: bool = False


class MemberPromote(BaseModel):
    new_role: MemberRole


class MemberResponse(BaseModel):
    id: uuid.UUID
    role: MemberRole
    display_handle: str | None = None
    joined_at: datetime
    circle_id: uuid.UUID | None = None
