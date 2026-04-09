import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import TransferStatus


class TransferRequest(BaseModel):
    deadline_hours: int | None = None


class TransferResponse(BaseModel):
    id: uuid.UUID
    status: TransferStatus
    deadline: datetime
    created_at: datetime
