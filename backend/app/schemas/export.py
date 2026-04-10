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

from pydantic import BaseModel

from app.models.enums import ModResponseScope, TopicStatus


class ExportedAttachment(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    storage_key: str
    created_at: datetime


class ExportedModResponse(BaseModel):
    id: uuid.UUID
    body: str
    scope: ModResponseScope
    created_at: datetime


class ExportedReply(BaseModel):
    id: uuid.UUID
    body: str
    display_handle: str | None
    created_at: datetime
    mod_response: ExportedModResponse | None = None


class ExportedUpdate(BaseModel):
    id: uuid.UUID
    title: str | None
    body: str
    circle_ids: list[uuid.UUID]
    attachments: list[ExportedAttachment]
    replies: list[ExportedReply]
    created_at: datetime


class ExportedCircle(BaseModel):
    id: uuid.UUID
    name: str
    member_count: int


class ExportedTopicMeta(BaseModel):
    id: uuid.UUID
    default_title: str
    status: TopicStatus
    short_code: str | None
    created_at: datetime
    closed_at: datetime | None


class TopicExport(BaseModel):
    meta: ExportedTopicMeta
    circles: list[ExportedCircle]
    updates: list[ExportedUpdate]
    exported_at: datetime
