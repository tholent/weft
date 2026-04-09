import uuid
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Token(SQLModel, table=True):
    __tablename__ = "token"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    member_id: uuid.UUID = Field(foreign_key="member.id")
    token_hash: str = Field(unique=True, index=True)
    revoked_at: datetime | None = Field(default=None)
    last_used_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
