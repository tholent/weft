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

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import TopicStatus


class TopicCreate(BaseModel):
    default_title: str = Field(min_length=1, max_length=200)
    creator_email: EmailStr | None = None


class TopicResponse(BaseModel):
    id: uuid.UUID
    default_title: str
    status: TopicStatus
    created_at: datetime
    closed_at: datetime | None = None
    scoped_title: str | None = None


class TopicCreateResponse(BaseModel):
    topic: TopicResponse
    magic_link: str
