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

from sqlalchemy import and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.circle import Circle
from app.models.member import MemberCircleHistory
from app.models.update import Update, UpdateCircle


async def create_update(
    session: AsyncSession,
    topic_id: uuid.UUID,
    author_member_id: uuid.UUID,
    body: str,
    circle_ids: list[uuid.UUID],
    circle_bodies: dict[str, str] | None = None,
) -> Update:
    """Create an update and stamp it to the given circles.

    circle_bodies maps str(circle_id) to a variant body for that circle.
    Circles without an entry use the parent update body.
    """
    # Validate all circles belong to topic
    for cid in circle_ids:
        result = await session.execute(select(Circle).where(Circle.id == cid))
        circle = result.scalar_one_or_none()
        if circle is None or circle.topic_id != topic_id:
            raise ValueError(f"Circle {cid} does not belong to topic {topic_id}")

    update = Update(topic_id=topic_id, author_member_id=author_member_id, body=body)
    session.add(update)
    await session.flush()

    # Create immutable update_circle rows
    variants = circle_bodies or {}
    for cid in circle_ids:
        variant_body = variants.get(str(cid))
        uc = UpdateCircle(update_id=update.id, circle_id=cid, body=variant_body)
        session.add(uc)

    await session.flush()
    return update


async def edit_update(
    session: AsyncSession,
    update_id: uuid.UUID,
    body: str,
) -> Update:
    """Edit the body of an update. update_circle rows are immutable and never changed."""
    result = await session.execute(select(Update).where(Update.id == update_id))
    update = result.scalar_one_or_none()
    if update is None:
        raise ValueError("Update not found")

    update.body = body
    update.edited_at = datetime.now(UTC)
    session.add(update)

    await session.flush()
    return update


async def soft_delete_update(session: AsyncSession, update_id: uuid.UUID) -> Update:
    result = await session.execute(select(Update).where(Update.id == update_id))
    update = result.scalar_one_or_none()
    if update is None:
        raise ValueError("Update not found")

    update.deleted_at = datetime.now(UTC)
    session.add(update)
    await session.flush()
    return update


async def get_feed(session: AsyncSession, member_id: uuid.UUID) -> list[Update]:
    """Get visible updates for a member based on their circle membership history."""
    # Get member's circle history
    history_result = await session.execute(
        select(MemberCircleHistory).where(MemberCircleHistory.member_id == member_id)
    )
    history_rows = history_result.scalars().all()

    if not history_rows:
        return []

    # Build visibility conditions: for each history window, the update must have been
    # stamped to that circle AND created within the access window.
    conditions = []
    for h in history_rows:
        time_cond = Update.created_at >= h.granted_at
        if h.revoked_at is not None:
            time_cond = and_(time_cond, Update.created_at < h.revoked_at)

        conditions.append(
            and_(
                UpdateCircle.circle_id == h.circle_id,
                time_cond,
            )
        )

    stmt = (
        select(Update)
        .join(UpdateCircle, Update.id == UpdateCircle.update_id)
        .where(or_(*conditions))
        .where(Update.deleted_at.is_(None))  # type: ignore[union-attr]
        .distinct()
        .order_by(Update.created_at.desc())  # type: ignore[union-attr]
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_updates_for_topic(
    session: AsyncSession,
    topic_id: uuid.UUID,
    circle_ids: list[uuid.UUID] | None = None,
) -> list[Update]:
    stmt = select(Update).where(
        Update.topic_id == topic_id,
        Update.deleted_at.is_(None),  # type: ignore[union-attr]
    )
    if circle_ids:
        stmt = (
            stmt.join(UpdateCircle, Update.id == UpdateCircle.update_id)
            .where(UpdateCircle.circle_id.in_(circle_ids))  # type: ignore[union-attr]
            .distinct()
        )
    stmt = stmt.order_by(Update.created_at.desc())  # type: ignore[union-attr]
    result = await session.execute(stmt)
    return list(result.scalars().all())
