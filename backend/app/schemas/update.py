# Copyright 2026 Chris Wells <chris@tholent.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UpdateCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)
    circle_ids: list[uuid.UUID] = Field(min_length=1)
    circle_bodies: dict[str, str] = Field(default_factory=dict)  # str(circle_id) → variant body


class UpdateEdit(BaseModel):
    body: str = Field(min_length=1, max_length=10000)
    circle_bodies: dict[str, str] = Field(default_factory=dict)  # str(circle_id) → updated variant body


class UpdateResponse(BaseModel):
    id: uuid.UUID
    body: str
    author_member_id: uuid.UUID
    author_handle: str | None = None
    circle_ids: list[uuid.UUID] = []
    body_variants: dict[str, str] = {}  # str(circle_id) → variant body; mods only
    created_at: datetime
    edited_at: datetime | None = None
    deleted_at: datetime | None = None
    reply_count: int = 0
    pending_reply_count: int = 0
