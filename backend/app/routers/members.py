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

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.session import get_session
from app.deps import require_topic_admin, require_topic_creator, require_topic_member
from app.models.enums import MemberRole
from app.models.member import Member, MemberCircleHistory
from app.schemas.member import MemberInvite, MemberMove, MemberPromote, MemberRename, MemberResponse
from app.schemas.pagination import PaginatedResponse
from app.services.auth import create_magic_link
from app.services.email import send_invite_email
from app.services.member import invite_member, list_members, move_member, promote_member

router = APIRouter(prefix="/topics/{topic_id}/members", tags=["members"])


@router.post("", response_model=MemberResponse)
async def invite_member_endpoint(
    topic_id: uuid.UUID,
    payload: MemberInvite,
    member: Member = Depends(require_topic_admin),
    session: AsyncSession = Depends(get_session),
):
    """Invite a member. Admin+ only. Sends invite email with magic link."""
    try:
        new_member, raw_token = await invite_member(
            session, topic_id, payload.email, payload.circle_id, payload.role
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    magic_link = create_magic_link(str(new_member.id))

    from app.services.topic import get_topic

    topic = await get_topic(session, topic_id)
    await send_invite_email(payload.email, topic.default_title, magic_link)

    return MemberResponse(
        id=new_member.id,
        role=new_member.role,
        display_handle=new_member.display_handle,
        joined_at=new_member.joined_at,
        circle_id=payload.circle_id,
    )


@router.get("", response_model=PaginatedResponse[MemberResponse])
async def list_members_endpoint(
    topic_id: uuid.UUID,
    member: Member = Depends(require_topic_member),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List members. Admin+ sees all; moderators see their circles; recipients see nothing."""
    if member.role == MemberRole.recipient:
        return PaginatedResponse(items=[], total=0, limit=limit, offset=offset)

    if member.role in (MemberRole.creator, MemberRole.admin):
        all_members = await list_members(session, topic_id)
    else:
        # Moderator: members in their circles only
        result = await session.execute(
            select(MemberCircleHistory.circle_id).where(
                MemberCircleHistory.member_id == member.id,
                MemberCircleHistory.revoked_at.is_(None),  # type: ignore[union-attr]
            )
        )
        circle_ids = list(result.scalars().all())
        all_members = []
        seen: set[uuid.UUID] = set()
        for cid in circle_ids:
            for m in await list_members(session, topic_id, cid):
                if m.id not in seen:
                    seen.add(m.id)
                    all_members.append(m)

    total = len(all_members)
    page = all_members[offset : offset + limit]

    # Get active circle for each member in the page
    responses = []
    for m in page:
        result = await session.execute(
            select(MemberCircleHistory).where(
                MemberCircleHistory.member_id == m.id,
                MemberCircleHistory.revoked_at.is_(None),  # type: ignore[union-attr]
            )
        )
        active = result.scalars().first()
        responses.append(
            MemberResponse(
                id=m.id,
                role=m.role,
                display_handle=m.display_handle,
                joined_at=m.joined_at,
                circle_id=active.circle_id if active else None,
            )
        )

    return PaginatedResponse(items=responses, total=total, limit=limit, offset=offset)


@router.patch("/{member_id}/circle")
async def move_member_endpoint(
    topic_id: uuid.UUID,
    member_id: uuid.UUID,
    payload: MemberMove,
    member: Member = Depends(require_topic_admin),
    session: AsyncSession = Depends(get_session),
):
    """Move a member to a different circle. Admin+ only."""
    await move_member(session, member_id, payload.new_circle_id, payload.retroactive_revoke)
    return {"detail": "Member moved"}


@router.patch("/{member_id}/role")
async def promote_member_endpoint(
    topic_id: uuid.UUID,
    member_id: uuid.UUID,
    payload: MemberPromote,
    member: Member = Depends(require_topic_member),
    session: AsyncSession = Depends(get_session),
):
    """Promote a member. Admin+ for moderator; creator only for admin."""
    try:
        updated = await promote_member(session, member_id, payload.new_role, member)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return {"detail": f"Member promoted to {updated.role.value}"}


@router.patch("/{member_id}/handle")
async def rename_member_endpoint(
    topic_id: uuid.UUID,
    member_id: uuid.UUID,
    payload: MemberRename,
    member: Member = Depends(require_topic_creator),
    session: AsyncSession = Depends(get_session),
):
    """Set a member's display handle. Creator only."""
    result = await session.execute(select(Member).where(Member.id == member_id))
    target = result.scalar_one_or_none()
    if target is None or target.topic_id != topic_id:
        raise HTTPException(status_code=404, detail="Member not found")
    target.display_handle = payload.display_handle
    session.add(target)
    return {"detail": "Handle updated"}


@router.post("/{member_id}/resend-invite")
async def resend_invite_endpoint(
    topic_id: uuid.UUID,
    member_id: uuid.UUID,
    member: Member = Depends(require_topic_admin),
    session: AsyncSession = Depends(get_session),
):
    """Re-send invite link. Admin+ only."""
    result = await session.execute(select(Member).where(Member.id == member_id))
    target = result.scalar_one_or_none()
    if target is None or target.email is None:
        raise HTTPException(status_code=400, detail="Member not found or has no email")

    magic_link = create_magic_link(str(target.id))

    from app.services.topic import get_topic

    topic = await get_topic(session, topic_id)
    await send_invite_email(target.email, topic.default_title, magic_link)

    return {"detail": "Invite re-sent"}
