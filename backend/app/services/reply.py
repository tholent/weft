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

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.enums import MemberRole, ModResponseScope, RelayStatus
from app.models.member import Member, MemberCircleHistory
from app.models.reply import ModResponse, Relay, Reply


async def create_reply(
    session: AsyncSession,
    update_id: uuid.UUID,
    author_member_id: uuid.UUID,
    body: str,
    wants_to_share: bool = False,
    author_role: MemberRole = MemberRole.recipient,
) -> Reply:
    # Replies from moderators and above bypass the moderation queue
    auto_relay = author_role in (MemberRole.owner, MemberRole.admin, MemberRole.moderator)
    reply = Reply(
        update_id=update_id,
        author_member_id=author_member_id,
        body=body,
        wants_to_share=wants_to_share,
        relay_status=RelayStatus.relayed if auto_relay else RelayStatus.pending,
    )
    session.add(reply)
    await session.flush()
    return reply


async def relay_reply(
    session: AsyncSession,
    reply_id: uuid.UUID,
    relayed_by_member_id: uuid.UUID,
    circle_ids: list[uuid.UUID] | None = None,
) -> list[Relay]:
    """Relay a reply to specified circles, or all circles if None."""
    relays = []
    if circle_ids is None:
        relay = Relay(
            reply_id=reply_id,
            relayed_by_member_id=relayed_by_member_id,
            circle_id=None,
        )
        session.add(relay)
        relays.append(relay)
    else:
        for cid in circle_ids:
            relay = Relay(
                reply_id=reply_id,
                relayed_by_member_id=relayed_by_member_id,
                circle_id=cid,
            )
            session.add(relay)
            relays.append(relay)

    # Update reply status
    result = await session.execute(select(Reply).where(Reply.id == reply_id))
    reply = result.scalar_one()
    reply.relay_status = RelayStatus.relayed
    session.add(reply)

    await session.flush()
    return relays


async def dismiss_reply(session: AsyncSession, reply_id: uuid.UUID) -> Reply:
    result = await session.execute(select(Reply).where(Reply.id == reply_id))
    reply = result.scalar_one_or_none()
    if reply is None:
        raise ValueError("Reply not found")

    reply.relay_status = RelayStatus.dismissed
    session.add(reply)
    await session.flush()
    return reply


async def create_mod_response(
    session: AsyncSession,
    reply_id: uuid.UUID,
    author_member_id: uuid.UUID,
    body: str,
    scope: ModResponseScope,
) -> ModResponse:
    mod_resp = ModResponse(
        reply_id=reply_id,
        author_member_id=author_member_id,
        body=body,
        scope=scope,
    )
    session.add(mod_resp)
    await session.flush()
    return mod_resp


async def get_replies_for_update(
    session: AsyncSession,
    update_id: uuid.UUID,
    viewer_member: Member,
) -> list[Reply]:
    """Get replies visible to the viewer.

    Moderators+ see all replies. Recipients see their own + relayed to their circles.
    """
    if viewer_member.role in (MemberRole.owner, MemberRole.admin, MemberRole.moderator):
        result = await session.execute(
            select(Reply)
            .where(Reply.update_id == update_id)
            .order_by(Reply.created_at)  # type: ignore[union-attr]
        )
        return list(result.scalars().all())

    # Recipient: own replies
    own_result = await session.execute(
        select(Reply).where(
            Reply.update_id == update_id,
            Reply.author_member_id == viewer_member.id,
        )
    )
    own_replies = list(own_result.scalars().all())

    # Recipient: relayed replies visible to their circle(s)
    # Get viewer's active circles
    circle_result = await session.execute(
        select(MemberCircleHistory.circle_id).where(
            MemberCircleHistory.member_id == viewer_member.id,
            MemberCircleHistory.revoked_at.is_(None),  # type: ignore[union-attr]
        )
    )
    viewer_circle_ids = [row for row in circle_result.scalars().all()]

    relayed_result = await session.execute(
        select(Reply)
        .join(Relay, Reply.id == Relay.reply_id)
        .where(
            Reply.update_id == update_id,
            Reply.relay_status == RelayStatus.relayed,
            # Relay to all circles (null) or to viewer's circle
            (Relay.circle_id.is_(None)) | (Relay.circle_id.in_(viewer_circle_ids)),  # type: ignore[union-attr]
        )
    )
    relayed_replies = list(relayed_result.scalars().all())

    # Merge and deduplicate
    seen_ids = set()
    merged = []
    for reply in own_replies + relayed_replies:
        if reply.id not in seen_ids:
            seen_ids.add(reply.id)
            merged.append(reply)

    merged.sort(key=lambda r: r.created_at)
    return merged


async def get_mod_responses_for_reply(
    session: AsyncSession,
    reply_id: uuid.UUID,
    viewer_member: Member,
) -> list[ModResponse]:
    """Get mod responses visible to the viewer based on scope."""
    result = await session.execute(
        select(ModResponse)
        .where(ModResponse.reply_id == reply_id)
        .order_by(ModResponse.created_at)  # type: ignore[union-attr]
    )
    all_responses = list(result.scalars().all())

    if viewer_member.role in (MemberRole.owner, MemberRole.admin, MemberRole.moderator):
        return all_responses

    # Get the reply to check if viewer is the author
    reply_result = await session.execute(select(Reply).where(Reply.id == reply_id))
    reply = reply_result.scalar_one()

    # Get viewer's active circles
    circle_result = await session.execute(
        select(MemberCircleHistory.circle_id).where(
            MemberCircleHistory.member_id == viewer_member.id,
            MemberCircleHistory.revoked_at.is_(None),  # type: ignore[union-attr]
        )
    )
    viewer_circle_ids = set(circle_result.scalars().all())

    # Get reply author's active circles
    author_circle_result = await session.execute(
        select(MemberCircleHistory.circle_id).where(
            MemberCircleHistory.member_id == reply.author_member_id,
            MemberCircleHistory.revoked_at.is_(None),  # type: ignore[union-attr]
        )
    )
    author_circle_ids = set(author_circle_result.scalars().all())

    visible = []
    for resp in all_responses:
        if resp.scope == ModResponseScope.all_circles:
            visible.append(resp)
        elif resp.scope == ModResponseScope.sender_circle:
            # Visible if viewer shares a circle with the reply author
            if viewer_circle_ids & author_circle_ids:
                visible.append(resp)
        elif resp.scope == ModResponseScope.sender_only:
            # Only the reply author sees this
            if viewer_member.id == reply.author_member_id:
                visible.append(resp)

    return visible
