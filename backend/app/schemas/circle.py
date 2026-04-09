import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class CircleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    scoped_title: str | None = Field(default=None, max_length=200)


class CircleUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    scoped_title: str | None = Field(default=None, max_length=200)
    clear_scoped_title: bool = False

    @model_validator(mode="after")
    def check_at_least_one_field(self) -> "CircleUpdate":
        if self.name is None and self.scoped_title is None and not self.clear_scoped_title:
            raise ValueError("At least one field must be provided")
        return self


class CircleResponse(BaseModel):
    id: uuid.UUID
    name: str
    scoped_title: str | None = None
    created_at: datetime
