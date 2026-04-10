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

from pydantic import BaseModel, EmailStr, field_validator

from app.models.enums import MemberRole, NotificationChannel


class MemberInvite(BaseModel):
    email: EmailStr | None = None
    phone: str | None = None
    circle_id: uuid.UUID
    role: MemberRole = MemberRole.recipient
    display_handle: str | None = None
    notification_channel: NotificationChannel = NotificationChannel.email

    @field_validator("role")
    @classmethod
    def validate_invite_role(cls, v: MemberRole) -> MemberRole:
        if v not in (MemberRole.recipient, MemberRole.moderator):
            raise ValueError(
                "Invited members can only be assigned recipient or moderator roles"
            )
        # admin and owner roles are only reachable through promotion or transfer
        return v


class MemberMove(BaseModel):
    new_circle_id: uuid.UUID
    retroactive_revoke: bool = False


class MemberPromote(BaseModel):
    new_role: MemberRole


class MemberRename(BaseModel):
    display_handle: str


class MemberResponse(BaseModel):
    id: uuid.UUID
    role: MemberRole
    display_handle: str | None = None
    joined_at: datetime
    circle_id: uuid.UUID | None = None
    notification_channel: NotificationChannel = NotificationChannel.email
    has_email: bool = False
    has_phone: bool = False
