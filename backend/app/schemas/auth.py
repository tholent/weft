import uuid

from pydantic import BaseModel

from app.models.enums import MemberRole


class MagicLinkVerify(BaseModel):
    token: str


class AuthResponse(BaseModel):
    token: str
    member_id: uuid.UUID
    role: MemberRole
    topic_id: uuid.UUID
