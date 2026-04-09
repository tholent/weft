import uuid
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Update(SQLModel, table=True):
    __tablename__ = "update"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    topic_id: uuid.UUID = Field(foreign_key="topic.id")
    author_member_id: uuid.UUID = Field(foreign_key="member.id")
    body: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    edited_at: datetime | None = Field(default=None)
    deleted_at: datetime | None = Field(default=None)


class UpdateCircle(SQLModel, table=True):
    """Immutable after insert. Records the audience stamped at post time."""

    __tablename__ = "update_circle"

    update_id: uuid.UUID = Field(foreign_key="update.id", primary_key=True)
    circle_id: uuid.UUID = Field(foreign_key="circle.id", primary_key=True)
    stamped_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
