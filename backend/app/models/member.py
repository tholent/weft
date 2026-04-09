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
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from app.models.enums import MemberRole


class Member(SQLModel, table=True):
    __tablename__ = "member"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    topic_id: uuid.UUID = Field(foreign_key="topic.id")
    role: MemberRole
    email: str | None = Field(default=None)
    display_handle: str | None = Field(default=None)
    joined_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    email_purged_at: datetime | None = Field(default=None)


class MemberCircleHistory(SQLModel, table=True):
    __tablename__ = "member_circle_history"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    member_id: uuid.UUID = Field(foreign_key="member.id")
    circle_id: uuid.UUID = Field(foreign_key="circle.id")
    granted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    revoked_at: datetime | None = Field(default=None)
