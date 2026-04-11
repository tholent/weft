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

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Annotated

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
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Member:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    raw_token = auth_header.removeprefix("Bearer ").strip()
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    token_result = await session.execute(select(Token).where(Token.token_hash == token_hash))
    token_row = token_result.scalar_one_or_none()
    if token_row is None or token_row.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Invalid or revoked token")

    member_result = await session.execute(select(Member).where(Member.id == token_row.member_id))
    member = member_result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=401, detail="Member not found")

    # Check topic status
    topic_result = await session.execute(select(Topic).where(Topic.id == member.topic_id))
    topic = topic_result.scalar_one_or_none()
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    if topic.status in (TopicStatus.closed, TopicStatus.archived):
        raise HTTPException(status_code=403, detail=f"Topic is {topic.status.value}")

    # Update last_used_at
    token_row.last_used_at = datetime.now(UTC)
    session.add(token_row)

    # If owner authenticates, cancel any pending dead-man's-switch transfer
    if member.role == MemberRole.owner:
        transfer_result = await session.execute(
            select(CreatorTransfer).where(
                CreatorTransfer.topic_id == member.topic_id,
                CreatorTransfer.status == TransferStatus.pending,
            )
        )
        pending_transfer = transfer_result.scalar_one_or_none()
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
    member: Annotated[Member, Depends(get_current_member)],
) -> Member:
    _verify_topic_access(member, topic_id)
    return member


async def require_topic_moderator(
    topic_id: uuid.UUID,
    member: Annotated[Member, Depends(get_current_member)],
) -> Member:
    _verify_topic_access(member, topic_id)
    if member.role not in (MemberRole.owner, MemberRole.admin, MemberRole.moderator):
        raise HTTPException(status_code=403, detail="Moderator or above required")
    return member


async def require_topic_admin(
    topic_id: uuid.UUID,
    member: Annotated[Member, Depends(get_current_member)],
) -> Member:
    _verify_topic_access(member, topic_id)
    if member.role not in (MemberRole.owner, MemberRole.admin):
        raise HTTPException(status_code=403, detail="Admin or above required")
    return member


async def require_topic_owner(
    topic_id: uuid.UUID,
    member: Annotated[Member, Depends(get_current_member)],
) -> Member:
    _verify_topic_access(member, topic_id)
    if member.role != MemberRole.owner:
        raise HTTPException(status_code=403, detail="Owner required")
    return member


# Keep bare versions for non-topic-scoped endpoints (e.g., /auth/revoke)
async def require_moderator(
    member: Annotated[Member, Depends(get_current_member)],
) -> Member:
    if member.role not in (MemberRole.owner, MemberRole.admin, MemberRole.moderator):
        raise HTTPException(status_code=403, detail="Moderator or above required")
    return member


async def require_admin(
    member: Annotated[Member, Depends(get_current_member)],
) -> Member:
    if member.role not in (MemberRole.owner, MemberRole.admin):
        raise HTTPException(status_code=403, detail="Admin or above required")
    return member


async def require_owner(
    member: Annotated[Member, Depends(get_current_member)],
) -> Member:
    if member.role != MemberRole.owner:
        raise HTTPException(status_code=403, detail="Owner required")
    return member


# ---------------------------------------------------------------------------
# Public Annotated type aliases — import these in routers instead of
# using Depends() as a default-value parameter (S8410 / PEP-593 style).
# ---------------------------------------------------------------------------

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentMemberDep = Annotated[Member, Depends(get_current_member)]
TopicMemberDep = Annotated[Member, Depends(require_topic_member)]
TopicModeratorDep = Annotated[Member, Depends(require_topic_moderator)]
TopicAdminDep = Annotated[Member, Depends(require_topic_admin)]
TopicOwnerDep = Annotated[Member, Depends(require_topic_owner)]
ModeratorDep = Annotated[Member, Depends(require_moderator)]
AdminDep = Annotated[Member, Depends(require_admin)]
OwnerDep = Annotated[Member, Depends(require_owner)]
