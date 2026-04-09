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


class Token(SQLModel, table=True):
    __tablename__ = "token"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    member_id: uuid.UUID = Field(foreign_key="member.id")
    token_hash: str = Field(unique=True, index=True)
    revoked_at: datetime | None = Field(default=None)
    last_used_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
