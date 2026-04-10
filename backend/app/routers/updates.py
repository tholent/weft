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
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.session import get_session
from app.deps import require_topic_member, require_topic_moderator
from app.models.enums import MemberRole, RelayStatus
from app.models.member import Member, MemberCircleHistory
from app.models.reply import Reply
from app.models.update import UpdateCircle
from app.schemas.pagination import PaginatedResponse
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
    # Get UpdateCircle rows (id + variant body)
    result = await session.execute(select(UpdateCircle).where(UpdateCircle.update_id == update.id))
    uc_rows = list(result.scalars().all())
    circle_ids = [uc.circle_id for uc in uc_rows]

    # Get reply count (scoped by role)
    is_recipient = member and member.role == MemberRole.recipient
    if is_recipient:
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

    # Pending reply count for moderators+
    pending_reply_count = 0
    if not is_recipient:
        result = await session.execute(
            select(Reply).where(
                Reply.update_id == update.id,
                Reply.relay_status == RelayStatus.pending,
            )
        )
        pending_reply_count = len(result.scalars().all())

    # Get author handle
    result = await session.execute(select(Member).where(Member.id == update.author_member_id))
    author = result.scalar_one_or_none()

    # For recipients, resolve their circle's variant body if one exists
    resolved_body = update.body
    if is_recipient and member:
        result = await session.execute(
            select(UpdateCircle).where(
                UpdateCircle.update_id == update.id,
                UpdateCircle.circle_id.in_(  # type: ignore[union-attr]
                    select(MemberCircleHistory.circle_id).where(
                        MemberCircleHistory.member_id == member.id
                    )
                ),
            )
        )
        matching_uc = result.scalars().first()
        if matching_uc and matching_uc.body:
            resolved_body = matching_uc.body

    # For mods, expose variants that differ from the default body
    body_variants: dict[str, str] = {}
    if not is_recipient:
        body_variants = {str(uc.circle_id): uc.body for uc in uc_rows if uc.body is not None}

    return UpdateResponse(
        id=update.id,
        body=resolved_body,
        author_member_id=update.author_member_id,
        author_handle=author.display_handle if author else None,
        circle_ids=circle_ids if not is_recipient else [],
        body_variants=body_variants,
        created_at=update.created_at,
        edited_at=update.edited_at,
        deleted_at=update.deleted_at,
        reply_count=reply_count,
        pending_reply_count=pending_reply_count,
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
            session, topic_id, member.id, payload.body, payload.circle_ids, payload.circle_bodies
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return await _build_update_response(session, update, member)


@router.get("", response_model=PaginatedResponse[UpdateResponse])
async def get_feed_endpoint(
    topic_id: uuid.UUID,
    member: Member = Depends(require_topic_member),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get feed. Uses member's circle history for visibility."""
    if member.role in (MemberRole.owner, MemberRole.admin, MemberRole.moderator):
        all_updates = await list_updates_for_topic(session, topic_id)
    else:
        all_updates = await get_feed(session, member.id)

    total = len(all_updates)
    page = all_updates[offset : offset + limit]
    items = [await _build_update_response(session, u, member) for u in page]

    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


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

    updated = await edit_update(session, update_id, payload.body, payload.circle_bodies)
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
        MemberRole.owner,
        MemberRole.admin,
    ):
        raise HTTPException(status_code=403, detail="Not authorized to delete this update")

    await soft_delete_update(session, update_id)
    return {"detail": "Update deleted"}
