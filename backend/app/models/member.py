import uuid
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from app.models.enums import MemberRole


class Member(SQLModel, table=True):
    __tablename__ = "member"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    topic_id: uuid.UUID = Field(foreign_key="topic.id")
    role: MemberRole
    email: str | None = Field(default=None)
    display_handle: str | None = Field(default=None)
    joined_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    email_purged_at: datetime | None = Field(default=None)


class MemberCircleHistory(SQLModel, table=True):
    __tablename__ = "member_circle_history"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    member_id: uuid.UUID = Field(foreign_key="member.id")
    circle_id: uuid.UUID = Field(foreign_key="circle.id")
    granted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    revoked_at: datetime | None = Field(default=None)
