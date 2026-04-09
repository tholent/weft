import uuid
from datetime import datetime

from pydantic import BaseModel


class CircleCreate(BaseModel):
    name: str
    scoped_title: str | None = None


class CircleUpdate(BaseModel):
    name: str | None = None
    scoped_title: str | None = None


class CircleResponse(BaseModel):
    id: uuid.UUID
    name: str
    scoped_title: str | None = None
    created_at: datetime
