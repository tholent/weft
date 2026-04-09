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

from app.models.enums import MemberRole, TopicStatus
from app.models.member import Member
from app.models.topic import Topic
from app.services.auth import create_magic_link
from app.services.purge import purge_emails


async def create_topic(
    session: AsyncSession,
    default_title: str,
    creator_email: str | None = None,
) -> tuple[Topic, Member, str]:
    """Create a topic with a creator member. Returns (topic, member, magic_link)."""
    topic = Topic(default_title=default_title)
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
