import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import get_settings
from app.models.enums import MemberRole, TransferStatus
from app.models.member import Member
from app.models.transfer import CreatorTransfer


async def request_transfer(
    session: AsyncSession,
    topic_id: uuid.UUID,
    requesting_member_id: uuid.UUID,
) -> CreatorTransfer:
    """Request a creator transfer. Only admins can request."""
    result = await session.execute(
        select(Member).where(Member.id == requesting_member_id)
    )
    member = result.scalar_one_or_none()
    if member is None or member.role != MemberRole.admin:
        raise ValueError("Only admins can request a creator transfer")

    # Check no pending transfer exists
    result = await session.execute(
        select(CreatorTransfer).where(
            CreatorTransfer.topic_id == topic_id,
            CreatorTransfer.status == TransferStatus.pending,
        )
    )
    if result.scalar_one_or_none() is not None:
        raise ValueError("A transfer request is already pending for this topic")

    settings = get_settings()
    deadline = datetime.now(UTC) + timedelta(hours=settings.creator_transfer_deadline_hours)

    transfer = CreatorTransfer(
        topic_id=topic_id,
        requested_by_member_id=requesting_member_id,
        deadline=deadline,
    )
    session.add(transfer)
    await session.flush()
    return transfer


async def cancel_transfer(session: AsyncSession, topic_id: uuid.UUID) -> None:
    """Cancel pending transfer. Called from auth dependency when creator authenticates."""
    result = await session.execute(
        select(CreatorTransfer).where(
            CreatorTransfer.topic_id == topic_id,
            CreatorTransfer.status == TransferStatus.pending,
        )
    )
    transfer = result.scalar_one_or_none()
    if transfer is not None:
        transfer.status = TransferStatus.denied
        transfer.resolved_at = datetime.now(UTC)
        session.add(transfer)


async def execute_transfer(session: AsyncSession, transfer_id: uuid.UUID) -> None:
    """Execute a transfer: promote requesting admin to creator, demote current creator."""
    result = await session.execute(
        select(CreatorTransfer).where(CreatorTransfer.id == transfer_id)
    )
    transfer = result.scalar_one_or_none()
    if transfer is None:
        raise ValueError("Transfer not found")
    if transfer.status != TransferStatus.pending:
        raise ValueError("Transfer is not pending")
    if transfer.deadline > datetime.now(UTC):
        raise ValueError("Transfer deadline has not passed")

    # Get current creator
    result = await session.execute(
        select(Member).where(
            Member.topic_id == transfer.topic_id,
            Member.role == MemberRole.creator,
        )
    )
    current_creator = result.scalar_one()

    # Get requesting admin
    result = await session.execute(
        select(Member).where(Member.id == transfer.requested_by_member_id)
    )
    new_creator = result.scalar_one()

    # Swap roles
    current_creator.role = MemberRole.admin
    new_creator.role = MemberRole.creator
    session.add(current_creator)
    session.add(new_creator)

    transfer.status = TransferStatus.expired
    transfer.resolved_at = datetime.now(UTC)
    session.add(transfer)
