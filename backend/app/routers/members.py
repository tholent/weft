import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.deps import get_current_member, require_admin
from app.models.enums import MemberRole
from app.models.member import Member, MemberCircleHistory
from app.schemas.member import MemberInvite, MemberMove, MemberPromote, MemberResponse
from app.services.auth import create_magic_link, generate_token
from app.services.email import send_invite_email
from app.services.member import invite_member, list_members, move_member, promote_member

router = APIRouter(prefix="/topics/{topic_id}/members", tags=["members"])


@router.post("", response_model=MemberResponse)
async def invite_member_endpoint(
    topic_id: uuid.UUID,
    payload: MemberInvite,
    member: Member = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Invite a member. Admin+ only. Sends invite email with magic link."""
    try:
        new_member, raw_token = await invite_member(
            session, topic_id, payload.email, payload.circle_id, payload.role
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    magic_link = create_magic_link(str(new_member.id), raw_token)

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


@router.get("", response_model=list[MemberResponse])
async def list_members_endpoint(
    topic_id: uuid.UUID,
    member: Member = Depends(get_current_member),
    session: AsyncSession = Depends(get_session),
):
    """List members. Admin+ sees all; moderators see their circles; recipients see nothing."""
    if member.role == MemberRole.recipient:
        return []

    if member.role in (MemberRole.creator, MemberRole.admin):
        members = await list_members(session, topic_id)
    else:
        # Moderator: members in their circles only
        from sqlmodel import select

        result = await session.execute(
            select(MemberCircleHistory.circle_id).where(
                MemberCircleHistory.member_id == member.id,
                MemberCircleHistory.revoked_at.is_(None),  # type: ignore[union-attr]
            )
        )
        circle_ids = list(result.scalars().all())
        members = []
        for cid in circle_ids:
            members.extend(await list_members(session, topic_id, cid))
        # Deduplicate
        seen = set()
        unique = []
        for m in members:
            if m.id not in seen:
                seen.add(m.id)
                unique.append(m)
        members = unique

    # Get active circle for each member
    responses = []
    for m in members:
        from sqlmodel import select

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

    return responses


@router.patch("/{member_id}/circle")
async def move_member_endpoint(
    topic_id: uuid.UUID,
    member_id: uuid.UUID,
    payload: MemberMove,
    member: Member = Depends(require_admin),
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
    member: Member = Depends(get_current_member),
    session: AsyncSession = Depends(get_session),
):
    """Promote a member. Admin+ for moderator; creator only for admin."""
    try:
        updated = await promote_member(session, member_id, payload.new_role, member)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return {"detail": f"Member promoted to {updated.role.value}"}


@router.post("/{member_id}/resend-invite")
async def resend_invite_endpoint(
    topic_id: uuid.UUID,
    member_id: uuid.UUID,
    member: Member = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Re-send invite link. Admin+ only."""
    from sqlmodel import select

    result = await session.execute(select(Member).where(Member.id == member_id))
    target = result.scalar_one_or_none()
    if target is None or target.email is None:
        raise HTTPException(status_code=400, detail="Member not found or has no email")

    raw_token = await generate_token(session, target.id)
    magic_link = create_magic_link(str(target.id), raw_token)

    from app.services.topic import get_topic

    topic = await get_topic(session, topic_id)
    await send_invite_email(target.email, topic.default_title, magic_link)

    return {"detail": "Invite re-sent"}
