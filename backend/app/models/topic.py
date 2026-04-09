import uuid
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from app.models.enums import TopicStatus


class Topic(SQLModel, table=True):
    __tablename__ = "topic"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    default_title: str
    status: TopicStatus = Field(default=TopicStatus.active)
    transfer_deadline: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    closed_at: datetime | None = Field(default=None)
