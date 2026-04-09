import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

from app.models.enums import MemberRole


class MemberInvite(BaseModel):
    email: EmailStr
    circle_id: uuid.UUID
    role: MemberRole = MemberRole.recipient

    @field_validator("role")
    @classmethod
    def validate_invite_role(cls, v: MemberRole) -> MemberRole:
        if v not in (MemberRole.recipient, MemberRole.moderator):
            raise ValueError("Invited members can only be assigned recipient or moderator roles")
        return v


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
