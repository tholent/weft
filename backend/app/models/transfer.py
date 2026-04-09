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
