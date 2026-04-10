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
from app.models.enums import MemberRole, NotificationChannel
from app.models.member import Member, MemberCircleHistory
from app.services.auth import generate_token
from app.services.notifications.preferences import create_defaults


async def invite_member(
    session: AsyncSession,
    topic_id: uuid.UUID,
    circle_id: uuid.UUID,
    role: MemberRole = MemberRole.recipient,
    email: str | None = None,
    phone: str | None = None,
    display_handle: str | None = None,
    notification_channel: NotificationChannel = NotificationChannel.email,
) -> tuple[Member, str]:
    """Invite a member to a topic. Returns (member, raw_token)."""
    if role == MemberRole.owner:
        raise ValueError("Cannot invite members as creator")
    if email is None and phone is None:
        raise ValueError("At least one of email or phone must be provided")
    if notification_channel == NotificationChannel.email and email is None:
        raise ValueError("Email is required when notification_channel is email")
    if notification_channel == NotificationChannel.sms and phone is None:
        raise ValueError("Phone is required when notification_channel is sms")
    # Validate circle belongs to topic
    result = await session.execute(select(Circle).where(Circle.id == circle_id))
    circle = result.scalar_one_or_none()
    if circle is None or circle.topic_id != topic_id:
        raise ValueError("Circle does not belong to this topic")

    member = Member(
        topic_id=topic_id,
        role=role,
        email=email,
        phone=phone,
        display_handle=display_handle or None,
        notification_channel=notification_channel,
    )
    session.add(member)
    await session.flush()

    # Create circle history
    history = MemberCircleHistory(member_id=member.id, circle_id=circle_id)
    session.add(history)

    # Create default notification preferences for the new member
    await create_defaults(session, member.id, notification_channel)

    raw_token = await generate_token(session, member.id)
    return member, raw_token


async def move_member(
    session: AsyncSession,
    member_id: uuid.UUID,
    new_circle_id: uuid.UUID,
    retroactive_revoke: bool = False,
) -> None:
    """Move a member to a different circle."""
    now = datetime.now(UTC)

    # Revoke current active circle history rows
    result = await session.execute(
        select(MemberCircleHistory).where(
            MemberCircleHistory.member_id == member_id,
            MemberCircleHistory.revoked_at.is_(None),  # type: ignore[union-attr]
        )
    )
    for history in result.scalars().all():
        if retroactive_revoke:
            history.revoked_at = history.granted_at
        else:
            history.revoked_at = now
        session.add(history)

    # Create new history row
    new_history = MemberCircleHistory(
        member_id=member_id,
        circle_id=new_circle_id,
        granted_at=now,
    )
    session.add(new_history)


async def promote_member(
    session: AsyncSession,
    member_id: uuid.UUID,
    new_role: MemberRole,
    promoting_member: Member,
) -> Member:
    """Promote a member. Only creator can promote to admin. Cannot promote to creator."""
    if new_role == MemberRole.owner:
        raise ValueError("Cannot promote to creator — use the transfer mechanism")

    if new_role == MemberRole.admin and promoting_member.role != MemberRole.owner:
        raise ValueError("Only the creator can promote to admin")

    if new_role == MemberRole.moderator and promoting_member.role not in (
        MemberRole.owner,
        MemberRole.admin,
    ):
        raise ValueError("Only admin or creator can promote to moderator")

    result = await session.execute(select(Member).where(Member.id == member_id))
    member = result.scalar_one_or_none()
    if member is None:
        raise ValueError("Member not found")

    member.role = new_role
    session.add(member)
    await session.flush()
    return member


async def get_member_feed_circles(
    session: AsyncSession, member_id: uuid.UUID
) -> list[MemberCircleHistory]:
    result = await session.execute(
        select(MemberCircleHistory).where(MemberCircleHistory.member_id == member_id)
    )
    return list(result.scalars().all())


async def list_members(
    session: AsyncSession,
    topic_id: uuid.UUID,
    circle_id: uuid.UUID | None = None,
) -> list[Member]:
    stmt = select(Member).where(Member.topic_id == topic_id)
    if circle_id is not None:
        # Filter to members currently in this circle
        stmt = stmt.where(
            Member.id.in_(  # type: ignore[union-attr]
                select(MemberCircleHistory.member_id).where(
                    MemberCircleHistory.circle_id == circle_id,
                    MemberCircleHistory.revoked_at.is_(None),  # type: ignore[union-attr]
                )
            )
        )
    result = await session.execute(stmt)
    return list(result.scalars().all())
