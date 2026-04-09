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

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.member import Member


async def purge_emails(session: AsyncSession, topic_id: uuid.UUID) -> None:
    """Set email=None and email_purged_at=now for all members in a topic."""
    now = datetime.now(UTC)
    result = await session.execute(select(Member).where(Member.topic_id == topic_id))
    members = result.scalars().all()
    for member in members:
        if member.email is not None:
            member.email = None
            member.email_purged_at = now
            session.add(member)
