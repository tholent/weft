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

from app.models.enums import (
    DeliveryMode,
    NotificationChannel,
    NotificationStatus,
    NotificationTrigger,
)


class NotificationPreference(SQLModel, table=True):
    __tablename__ = "notification_preference"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    member_id: uuid.UUID = Field(foreign_key="member.id", index=True)
    channel: NotificationChannel
    trigger: NotificationTrigger
    delivery_mode: DeliveryMode = Field(default=DeliveryMode.immediate)


class NotificationLog(SQLModel, table=True):
    __tablename__ = "notification_log"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    member_id: uuid.UUID = Field(foreign_key="member.id", index=True)
    topic_id: uuid.UUID = Field(foreign_key="topic.id", index=True)
    channel: NotificationChannel
    trigger: NotificationTrigger
    status: NotificationStatus = Field(default=NotificationStatus.pending)
    provider_message_id: str | None = Field(default=None)
    error_detail: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    sent_at: datetime | None = Field(default=None)
