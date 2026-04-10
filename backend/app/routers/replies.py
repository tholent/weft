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

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.session import get_session
from app.deps import require_topic_member, require_topic_moderator
from app.models.member import Member
from app.schemas.pagination import PaginatedResponse
from app.schemas.reply import (
    ModResponseCreate,
    ModResponseResponse,
    RelayAction,
    ReplyCreate,
    ReplyResponse,
)
from app.services.reply import (
    create_mod_response,
    create_reply,
    dismiss_reply,
    get_mod_responses_for_reply,
    get_replies_for_update,
    relay_reply,
)

router = APIRouter(prefix="/topics/{topic_id}/updates/{update_id}/replies", tags=["replies"])


@router.post("", response_model=ReplyResponse)
async def create_reply_endpoint(
    topic_id: uuid.UUID,
    update_id: uuid.UUID,
    payload: ReplyCreate,
    member: Member = Depends(require_topic_member),
    session: AsyncSession = Depends(get_session),
):
    """Create a reply to an update. Any authenticated member."""
    reply = await create_reply(
        session, update_id, member.id, payload.body, payload.wants_to_share, member.role
    )
    return ReplyResponse(
        id=reply.id,
        body=reply.body,
        author_member_id=reply.author_member_id,
        author_handle=member.display_handle,
        wants_to_share=reply.wants_to_share,
        relay_status=reply.relay_status,
        created_at=reply.created_at,
    )


@router.get("", response_model=PaginatedResponse[ReplyResponse])
async def list_replies_endpoint(
    topic_id: uuid.UUID,
    update_id: uuid.UUID,
    member: Member = Depends(require_topic_member),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List replies for an update. Scoped by role."""
    all_replies = await get_replies_for_update(session, update_id, member)

    total = len(all_replies)
    page = all_replies[offset : offset + limit]

    responses = []
    for reply in page:
        result = await session.execute(select(Member).where(Member.id == reply.author_member_id))
        author = result.scalar_one_or_none()

        mod_responses = await get_mod_responses_for_reply(session, reply.id, member)

        responses.append(
            ReplyResponse(
                id=reply.id,
                body=reply.body,
                author_member_id=reply.author_member_id,
                author_handle=author.display_handle if author else None,
                wants_to_share=reply.wants_to_share,
                relay_status=reply.relay_status,
                created_at=reply.created_at,
                mod_responses=[
                    ModResponseResponse(
                        id=mr.id,
                        body=mr.body,
                        author_handle=None,
                        scope=mr.scope,
                        created_at=mr.created_at,
                    )
                    for mr in mod_responses
                ],
            )
        )

    return PaginatedResponse(items=responses, total=total, limit=limit, offset=offset)


@router.post("/{reply_id}/relay")
async def relay_reply_endpoint(
    topic_id: uuid.UUID,
    update_id: uuid.UUID,
    reply_id: uuid.UUID,
    payload: RelayAction,
    member: Member = Depends(require_topic_moderator),
    session: AsyncSession = Depends(get_session),
):
    """Relay a reply to circles. Moderator+ only."""
    await relay_reply(session, reply_id, member.id, payload.circle_ids)
    return {"detail": "Reply relayed"}


@router.post("/{reply_id}/dismiss")
async def dismiss_reply_endpoint(
    topic_id: uuid.UUID,
    update_id: uuid.UUID,
    reply_id: uuid.UUID,
    member: Member = Depends(require_topic_moderator),
    session: AsyncSession = Depends(get_session),
):
    """Dismiss a reply. Moderator+ only."""
    await dismiss_reply(session, reply_id)
    return {"detail": "Reply dismissed"}


@router.post("/{reply_id}/respond", response_model=ModResponseResponse)
async def create_mod_response_endpoint(
    topic_id: uuid.UUID,
    update_id: uuid.UUID,
    reply_id: uuid.UUID,
    payload: ModResponseCreate,
    member: Member = Depends(require_topic_moderator),
    session: AsyncSession = Depends(get_session),
):
    """Create a mod response to a reply. Moderator+ only."""
    mod_resp = await create_mod_response(session, reply_id, member.id, payload.body, payload.scope)
    return ModResponseResponse(
        id=mod_resp.id,
        body=mod_resp.body,
        author_handle=member.display_handle,
        scope=mod_resp.scope,
        created_at=mod_resp.created_at,
    )
