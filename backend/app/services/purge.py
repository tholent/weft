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
