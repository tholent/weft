import hashlib
import uuid
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.session import get_session
from app.models.enums import MemberRole, TopicStatus, TransferStatus
from app.models.member import Member
from app.models.token import Token
from app.models.topic import Topic
from app.models.transfer import CreatorTransfer


async def get_current_member(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Member:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    raw_token = auth_header.removeprefix("Bearer ").strip()
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    result = await session.execute(select(Token).where(Token.token_hash == token_hash))
    token_row = result.scalar_one_or_none()
    if token_row is None or token_row.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Invalid or revoked token")

    result = await session.execute(select(Member).where(Member.id == token_row.member_id))
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=401, detail="Member not found")

    # Check topic status
    result = await session.execute(select(Topic).where(Topic.id == member.topic_id))
    topic = result.scalar_one_or_none()
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    if topic.status in (TopicStatus.closed, TopicStatus.archived):
        raise HTTPException(status_code=403, detail=f"Topic is {topic.status.value}")

    # Update last_used_at
    token_row.last_used_at = datetime.now(UTC)
    session.add(token_row)

    # If creator authenticates, cancel any pending transfer
    if member.role == MemberRole.creator:
        result = await session.execute(
            select(CreatorTransfer).where(
                CreatorTransfer.topic_id == member.topic_id,
                CreatorTransfer.status == TransferStatus.pending,
            )
        )
        pending_transfer = result.scalar_one_or_none()
        if pending_transfer is not None:
            pending_transfer.status = TransferStatus.denied
            pending_transfer.resolved_at = datetime.now(UTC)
            session.add(pending_transfer)

    return member


def _verify_topic_access(member: Member, topic_id: uuid.UUID) -> None:
    """Verify the member belongs to the requested topic."""
    if member.topic_id != topic_id:
        raise HTTPException(status_code=403, detail="Access denied: wrong topic")


async def require_topic_member(
    topic_id: uuid.UUID,
    member: Member = Depends(get_current_member),
) -> Member:
    _verify_topic_access(member, topic_id)
    return member


async def require_topic_moderator(
    topic_id: uuid.UUID,
    member: Member = Depends(get_current_member),
) -> Member:
    _verify_topic_access(member, topic_id)
    if member.role not in (MemberRole.creator, MemberRole.admin, MemberRole.moderator):
        raise HTTPException(status_code=403, detail="Moderator or above required")
    return member


async def require_topic_admin(
    topic_id: uuid.UUID,
    member: Member = Depends(get_current_member),
) -> Member:
    _verify_topic_access(member, topic_id)
    if member.role not in (MemberRole.creator, MemberRole.admin):
        raise HTTPException(status_code=403, detail="Admin or above required")
    return member


async def require_topic_creator(
    topic_id: uuid.UUID,
    member: Member = Depends(get_current_member),
) -> Member:
    _verify_topic_access(member, topic_id)
    if member.role != MemberRole.creator:
        raise HTTPException(status_code=403, detail="Creator required")
    return member


# Keep bare versions for non-topic-scoped endpoints (e.g., /auth/revoke)
async def require_moderator(
    member: Member = Depends(get_current_member),
) -> Member:
    if member.role not in (MemberRole.creator, MemberRole.admin, MemberRole.moderator):
        raise HTTPException(status_code=403, detail="Moderator or above required")
    return member


async def require_admin(
    member: Member = Depends(get_current_member),
) -> Member:
    if member.role not in (MemberRole.creator, MemberRole.admin):
        raise HTTPException(status_code=403, detail="Admin or above required")
    return member


async def require_creator(
    member: Member = Depends(get_current_member),
) -> Member:
    if member.role != MemberRole.creator:
        raise HTTPException(status_code=403, detail="Creator required")
    return member
