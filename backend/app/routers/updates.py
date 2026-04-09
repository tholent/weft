import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.session import get_session
from app.deps import require_topic_member, require_topic_moderator
from app.models.enums import MemberRole, RelayStatus
from app.models.member import Member
from app.models.reply import Reply
from app.models.update import UpdateCircle
from app.schemas.update import UpdateCreate, UpdateEdit, UpdateResponse
from app.services.update import (
    create_update,
    edit_update,
    get_feed,
    list_updates_for_topic,
    soft_delete_update,
)

router = APIRouter(prefix="/topics/{topic_id}/updates", tags=["updates"])


async def _build_update_response(
    session: AsyncSession, update, member: Member | None = None
) -> UpdateResponse:
    # Get circle IDs
    result = await session.execute(
        select(UpdateCircle.circle_id).where(UpdateCircle.update_id == update.id)
    )
    circle_ids = list(result.scalars().all())

    # Get reply count (scoped by role)
    if member and member.role == MemberRole.recipient:
        reply_query = select(Reply).where(
            Reply.update_id == update.id,
            or_(
                Reply.author_member_id == member.id,
                Reply.relay_status == RelayStatus.relayed,
            ),
        )
    else:
        reply_query = select(Reply).where(Reply.update_id == update.id)
    result = await session.execute(reply_query)
    reply_count = len(result.scalars().all())

    # Get author handle
    result = await session.execute(select(Member).where(Member.id == update.author_member_id))
    author = result.scalar_one_or_none()

    return UpdateResponse(
        id=update.id,
        body=update.body,
        author_member_id=update.author_member_id,
        author_handle=author.display_handle if author else None,
        circle_ids=circle_ids if member and member.role != MemberRole.recipient else [],
        created_at=update.created_at,
        edited_at=update.edited_at,
        deleted_at=update.deleted_at,
        reply_count=reply_count,
    )


@router.post("", response_model=UpdateResponse)
async def create_update_endpoint(
    topic_id: uuid.UUID,
    payload: UpdateCreate,
    member: Member = Depends(require_topic_moderator),
    session: AsyncSession = Depends(get_session),
):
    """Create an update addressed to specified circles. Moderator+ only."""
    try:
        update = await create_update(
            session, topic_id, member.id, payload.body, payload.circle_ids
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return await _build_update_response(session, update, member)


@router.get("", response_model=list[UpdateResponse])
async def get_feed_endpoint(
    topic_id: uuid.UUID,
    member: Member = Depends(require_topic_member),
    session: AsyncSession = Depends(get_session),
):
    """Get feed. Uses member's circle history for visibility."""
    if member.role in (MemberRole.creator, MemberRole.admin, MemberRole.moderator):
        updates = await list_updates_for_topic(session, topic_id)
    else:
        updates = await get_feed(session, member.id)

    return [await _build_update_response(session, u, member) for u in updates]


@router.patch("/{update_id}", response_model=UpdateResponse)
async def edit_update_endpoint(
    topic_id: uuid.UUID,
    update_id: uuid.UUID,
    payload: UpdateEdit,
    member: Member = Depends(require_topic_member),
    session: AsyncSession = Depends(get_session),
):
    """Edit an update. Author only."""
    from app.models.update import Update

    result = await session.execute(select(Update).where(Update.id == update_id))
    update = result.scalar_one_or_none()
    if update is None:
        raise HTTPException(status_code=404, detail="Update not found")
    if update.author_member_id != member.id:
        raise HTTPException(status_code=403, detail="Only the author can edit")

    updated = await edit_update(session, update_id, payload.body)
    return await _build_update_response(session, updated, member)


@router.delete("/{update_id}")
async def delete_update_endpoint(
    topic_id: uuid.UUID,
    update_id: uuid.UUID,
    member: Member = Depends(require_topic_member),
    session: AsyncSession = Depends(get_session),
):
    """Soft delete an update. Author or admin+ only."""
    from app.models.update import Update

    result = await session.execute(select(Update).where(Update.id == update_id))
    update = result.scalar_one_or_none()
    if update is None:
        raise HTTPException(status_code=404, detail="Update not found")
    if update.author_member_id != member.id and member.role not in (
        MemberRole.creator,
        MemberRole.admin,
    ):
        raise HTTPException(status_code=403, detail="Not authorized to delete this update")

    await soft_delete_update(session, update_id)
    return {"detail": "Update deleted"}
