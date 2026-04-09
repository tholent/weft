import uuid
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from app.models.enums import TransferStatus


class CreatorTransfer(SQLModel, table=True):
    __tablename__ = "creator_transfer"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    topic_id: uuid.UUID = Field(foreign_key="topic.id")
    requested_by_member_id: uuid.UUID = Field(foreign_key="member.id")
    deadline: datetime
    status: TransferStatus = Field(default=TransferStatus.pending)
    resolved_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
