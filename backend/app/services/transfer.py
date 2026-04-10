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
    """Request a dead-man's-switch transfer. Only admins can request."""
    result = await session.execute(select(Member).where(Member.id == requesting_member_id))
    member = result.scalar_one_or_none()
    if member is None or member.role != MemberRole.admin:
        raise ValueError("Only admins can request an ownership transfer")

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
    """Cancel pending transfer. Called when owner authenticates."""
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
    """Execute a dead-man's-switch transfer.

    Promotes the requesting admin to owner and demotes the current owner.
    """
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

    # Get current owner
    result = await session.execute(
        select(Member).where(
            Member.topic_id == transfer.topic_id,
            Member.role == MemberRole.owner,
        )
    )
    current_owner = result.scalar_one()

    # Get requesting admin (becomes new owner)
    result = await session.execute(
        select(Member).where(Member.id == transfer.requested_by_member_id)
    )
    new_owner = result.scalar_one()

    current_owner.role = MemberRole.admin
    new_owner.role = MemberRole.owner
    session.add(current_owner)
    session.add(new_owner)

    transfer.status = TransferStatus.expired
    transfer.resolved_at = datetime.now(UTC)
    session.add(transfer)


async def execute_direct_transfer(
    session: AsyncSession,
    topic_id: uuid.UUID,
    target_member_id: uuid.UUID,
    owner_member_id: uuid.UUID,
) -> CreatorTransfer:
    """Immediately transfer ownership to any member. Owner only."""
    result = await session.execute(select(Member).where(Member.id == owner_member_id))
    owner = result.scalar_one_or_none()
    if owner is None or owner.role != MemberRole.owner:
        raise ValueError("Only the owner can directly transfer ownership")

    result = await session.execute(select(Member).where(Member.id == target_member_id))
    target = result.scalar_one_or_none()
    if target is None or target.topic_id != topic_id:
        raise ValueError("Target member not found in this topic")
    if target.id == owner.id:
        raise ValueError("Cannot transfer ownership to yourself")

    now = datetime.now(UTC)
    transfer = CreatorTransfer(
        topic_id=topic_id,
        requested_by_member_id=target_member_id,
        deadline=now,
        status=TransferStatus.confirmed,
        direct=True,
        resolved_at=now,
    )
    session.add(transfer)
    await session.flush()

    owner.role = MemberRole.admin
    target.role = MemberRole.owner
    session.add(owner)
    session.add(target)

    return transfer
