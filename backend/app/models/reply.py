import uuid
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from app.models.enums import ModResponseScope, RelayStatus


class Reply(SQLModel, table=True):
    __tablename__ = "reply"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    update_id: uuid.UUID = Field(foreign_key="update.id")
    author_member_id: uuid.UUID = Field(foreign_key="member.id")
    body: str
    wants_to_share: bool = Field(default=False)
    relay_status: RelayStatus = Field(default=RelayStatus.pending)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Relay(SQLModel, table=True):
    __tablename__ = "relay"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    reply_id: uuid.UUID = Field(foreign_key="reply.id")
    relayed_by_member_id: uuid.UUID = Field(foreign_key="member.id")
    circle_id: uuid.UUID | None = Field(default=None, foreign_key="circle.id")
    relayed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ModResponse(SQLModel, table=True):
    __tablename__ = "mod_response"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    reply_id: uuid.UUID = Field(foreign_key="reply.id")
    author_member_id: uuid.UUID = Field(foreign_key="member.id")
    body: str
    scope: ModResponseScope
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
