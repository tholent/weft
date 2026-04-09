import uuid
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Circle(SQLModel, table=True):
    __tablename__ = "circle"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    topic_id: uuid.UUID = Field(foreign_key="topic.id")
    name: str
    scoped_title: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    deleted_at: datetime | None = Field(default=None)
