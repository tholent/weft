import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.circle import Circle
from app.models.enums import MemberRole
from app.models.member import Member, MemberCircleHistory
from app.services.auth import generate_token


async def invite_member(
    session: AsyncSession,
    topic_id: uuid.UUID,
    email: str,
    circle_id: uuid.UUID,
    role: MemberRole = MemberRole.recipient,
) -> tuple[Member, str]:
    """Invite a member to a topic. Returns (member, raw_token)."""
    if role in (MemberRole.creator, MemberRole.admin):
        raise ValueError("Cannot invite members as admin or creator")
    # Validate circle belongs to topic
    result = await session.execute(select(Circle).where(Circle.id == circle_id))
    circle = result.scalar_one_or_none()
    if circle is None or circle.topic_id != topic_id:
        raise ValueError("Circle does not belong to this topic")

    member = Member(topic_id=topic_id, role=role, email=email)
    session.add(member)
    await session.flush()

    # Create circle history
    history = MemberCircleHistory(member_id=member.id, circle_id=circle_id)
    session.add(history)

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
    if new_role == MemberRole.creator:
        raise ValueError("Cannot promote to creator — use the transfer mechanism")

    if new_role == MemberRole.admin and promoting_member.role != MemberRole.creator:
        raise ValueError("Only the creator can promote to admin")

    if new_role == MemberRole.moderator and promoting_member.role not in (
        MemberRole.creator,
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
