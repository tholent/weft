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

from app.models.circle import Circle
from app.models.member import MemberCircleHistory


async def create_circle(
    session: AsyncSession,
    topic_id: uuid.UUID,
    name: str,
    scoped_title: str | None = None,
) -> Circle:
    circle = Circle(topic_id=topic_id, name=name, scoped_title=scoped_title)
    session.add(circle)
    await session.flush()
    return circle


async def rename_circle(
    session: AsyncSession,
    circle_id: uuid.UUID,
    topic_id: uuid.UUID,
    name: str | None = None,
    scoped_title: str | None = None,
    clear_scoped_title: bool = False,
) -> Circle:
    result = await session.execute(select(Circle).where(Circle.id == circle_id))
    circle = result.scalar_one_or_none()
    if circle is None or circle.topic_id != topic_id:
        raise ValueError("Circle not found")
    if name is not None:
        circle.name = name
    if clear_scoped_title:
        circle.scoped_title = None
    elif scoped_title is not None:
        circle.scoped_title = scoped_title
    session.add(circle)
    await session.flush()
    return circle


async def delete_circle(
    session: AsyncSession, circle_id: uuid.UUID, topic_id: uuid.UUID
) -> None:
    result = await session.execute(select(Circle).where(Circle.id == circle_id))
    circle = result.scalar_one_or_none()
    if circle is None or circle.topic_id != topic_id:
        raise ValueError("Circle not found")

    # Check for active members
    result = await session.execute(
        select(MemberCircleHistory).where(
            MemberCircleHistory.circle_id == circle_id,
            MemberCircleHistory.revoked_at.is_(None),  # type: ignore[union-attr]
        )
    )
    if result.scalars().first() is not None:
        raise ValueError("Cannot delete circle with active members")

    # Soft-delete to preserve update_circle and member_circle_history references
    circle.deleted_at = datetime.now(UTC)
    session.add(circle)


async def list_circles(session: AsyncSession, topic_id: uuid.UUID) -> list[Circle]:
    result = await session.execute(
        select(Circle).where(
            Circle.topic_id == topic_id,
            Circle.deleted_at.is_(None),  # type: ignore[union-attr]
        )
    )
    return list(result.scalars().all())
