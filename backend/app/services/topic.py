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

import random
import string
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.enums import MemberRole, TopicStatus
from app.models.member import Member
from app.models.topic import Topic
from app.services.auth import create_magic_link
from app.services.purge import purge_emails

_SHORT_CODE_CHARS = string.ascii_uppercase + string.digits
_SHORT_CODE_LEN = 3
_SHORT_CODE_MAX_ATTEMPTS = 10


async def generate_short_code(session: AsyncSession) -> str:
    """Generate a unique 3-character alphanumeric short code for a topic.

    Generates a random uppercase alphanumeric code and retries up to
    _SHORT_CODE_MAX_ATTEMPTS times to avoid collisions with active topics.

    Raises:
        RuntimeError: If a unique code cannot be generated within the retry limit.
    """
    for _ in range(_SHORT_CODE_MAX_ATTEMPTS):
        code = "".join(random.choices(_SHORT_CODE_CHARS, k=_SHORT_CODE_LEN))
        result = await session.execute(
            select(Topic).where(
                Topic.short_code == code,
                Topic.status == TopicStatus.active,
            )
        )
        if result.scalar_one_or_none() is None:
            return code
    raise RuntimeError(
        f"Failed to generate a unique short code after {_SHORT_CODE_MAX_ATTEMPTS} attempts"
    )


async def create_topic(
    session: AsyncSession,
    default_title: str,
    creator_email: str | None = None,
) -> tuple[Topic, Member, str]:
    """Create a topic with a creator member. Returns (topic, member, magic_link)."""
    short_code = await generate_short_code(session)
    topic = Topic(default_title=default_title, short_code=short_code)
    session.add(topic)
    await session.flush()

    member = Member(
        topic_id=topic.id,
        role=MemberRole.owner,
        email=creator_email,
    )
    session.add(member)
    await session.flush()

    magic_link = create_magic_link(str(member.id))

    return topic, member, magic_link


async def close_topic(session: AsyncSession, topic_id: uuid.UUID) -> Topic:
    result = await session.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()
    if topic is None:
        raise ValueError("Topic not found")

    topic.status = TopicStatus.closed
    topic.closed_at = datetime.now(UTC)
    session.add(topic)

    await purge_emails(session, topic_id)
    return topic


async def get_topic(session: AsyncSession, topic_id: uuid.UUID) -> Topic:
    result = await session.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()
    if topic is None:
        raise ValueError("Topic not found")
    return topic
