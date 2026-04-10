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

"""Topic export service.

Produces a structured, privacy-safe snapshot of a topic suitable for
JSON serialization and long-term archival. All PII (emails, phones, raw
member IDs) is excluded — only display handles and public metadata are
included.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.attachment import Attachment
from app.models.circle import Circle
from app.models.member import Member
from app.models.reply import ModResponse, Relay, Reply
from app.models.topic import Topic
from app.models.update import Update, UpdateCircle


async def export_topic(session: AsyncSession, topic_id: uuid.UUID) -> dict[str, Any]:
    """Export full topic data as a structured dict (for JSON serialization).

    The export includes topic metadata, circles, updates with replies and
    attachments, and relays. It excludes all PII (emails, phones) and
    internal IDs other than those needed for structural linkage within the
    export itself.

    Raises:
        ValueError: If the topic is not found.
    """
    # --- Load topic ---
    topic_result = await session.execute(select(Topic).where(Topic.id == topic_id))
    topic = topic_result.scalar_one_or_none()
    if topic is None:
        raise ValueError(f"Topic {topic_id} not found")

    # --- Load circles ---
    circles_result = await session.execute(select(Circle).where(Circle.topic_id == topic_id))
    circles = list(circles_result.scalars().all())
    circle_map: dict[uuid.UUID, Circle] = {c.id: c for c in circles}

    # --- Load members (for handle lookup only) ---
    members_result = await session.execute(select(Member).where(Member.topic_id == topic_id))
    member_map: dict[uuid.UUID, str | None] = {
        m.id: m.display_handle for m in members_result.scalars().all()
    }

    # --- Load updates ---
    updates_result = await session.execute(
        select(Update)
        .where(Update.topic_id == topic_id, Update.deleted_at.is_(None))  # type: ignore[union-attr]
        .order_by(Update.created_at)
    )
    updates = list(updates_result.scalars().all())

    # --- Load update→circle mappings ---
    if updates:
        update_ids = [u.id for u in updates]
        uc_result = await session.execute(
            select(UpdateCircle).where(UpdateCircle.update_id.in_(update_ids))  # type: ignore[union-attr]
        )
        uc_rows = list(uc_result.scalars().all())
    else:
        uc_rows = []

    update_circles: dict[uuid.UUID, list[str]] = {}
    for uc in uc_rows:
        circle = circle_map.get(uc.circle_id)
        circle_name = circle.name if circle else str(uc.circle_id)
        update_circles.setdefault(uc.update_id, []).append(circle_name)

    # --- Load attachments ---
    if updates:
        att_result = await session.execute(
            select(Attachment).where(Attachment.update_id.in_(update_ids))  # type: ignore[union-attr]
        )
        att_rows = list(att_result.scalars().all())
    else:
        att_rows = []

    update_attachments: dict[uuid.UUID, list[dict[str, Any]]] = {}
    for att in att_rows:
        update_attachments.setdefault(att.update_id, []).append(
            {
                "filename": att.filename,
                "content_type": att.content_type,
                "size_bytes": att.size_bytes,
                # storage_key is intentionally excluded — it is an internal
                # infrastructure detail and must never appear in exports.
            }
        )

    # --- Load replies ---
    if updates:
        replies_result = await session.execute(
            select(Reply).where(Reply.update_id.in_(update_ids)).order_by(Reply.created_at)  # type: ignore[union-attr]
        )
        replies = list(replies_result.scalars().all())
    else:
        replies = []

    reply_ids = [r.id for r in replies]

    # --- Load mod responses ---
    if reply_ids:
        mr_result = await session.execute(
            select(ModResponse)
            .where(ModResponse.reply_id.in_(reply_ids))  # type: ignore[union-attr]
            .order_by(ModResponse.created_at)
        )
        mod_responses = list(mr_result.scalars().all())
    else:
        mod_responses = []

    reply_mod_responses: dict[uuid.UUID, list[dict[str, Any]]] = {}
    for mr in mod_responses:
        reply_mod_responses.setdefault(mr.reply_id, []).append(
            {
                "body": mr.body,
                "author": member_map.get(mr.author_member_id),
                "scope": str(mr.scope),
                "created_at": mr.created_at.isoformat(),
            }
        )

    update_replies: dict[uuid.UUID, list[dict[str, Any]]] = {}
    for reply in replies:
        update_replies.setdefault(reply.update_id, []).append(
            {
                "body": reply.body,
                "author": member_map.get(reply.author_member_id),
                "wants_to_share": reply.wants_to_share,
                "relay_status": str(reply.relay_status),
                "created_at": reply.created_at.isoformat(),
                "mod_responses": reply_mod_responses.get(reply.id, []),
            }
        )

    # --- Load relays ---
    if reply_ids:
        relay_result = await session.execute(
            select(Relay)
            .where(Relay.reply_id.in_(reply_ids))  # type: ignore[union-attr]
            .order_by(Relay.relayed_at)
        )
        relays = list(relay_result.scalars().all())
    else:
        relays = []

    relays_export: list[dict[str, Any]] = [
        {
            "reply_id": str(relay.reply_id),
            "relayed_by": member_map.get(relay.relayed_by_member_id),
            "circle": (
                circle_map[relay.circle_id].name
                if relay.circle_id and relay.circle_id in circle_map
                else None
            ),
            "relayed_at": relay.relayed_at.isoformat(),
        }
        for relay in relays
    ]

    # --- Assemble export ---
    exported_circles = [
        {"name": c.name, "scoped_title": c.scoped_title} for c in circles if c.deleted_at is None
    ]

    exported_updates = [
        {
            "body": u.body,
            "author": member_map.get(u.author_member_id),
            "circles": update_circles.get(u.id, []),
            "attachments": update_attachments.get(u.id, []),
            "replies": update_replies.get(u.id, []),
            "created_at": u.created_at.isoformat(),
            "edited_at": u.edited_at.isoformat() if u.edited_at else None,
        }
        for u in updates
    ]

    return {
        "topic": {
            "title": topic.default_title,
            "status": str(topic.status),
            "created_at": topic.created_at.isoformat(),
            "closed_at": topic.closed_at.isoformat() if topic.closed_at else None,
        },
        "circles": exported_circles,
        "updates": exported_updates,
        "relays": relays_export,
        "exported_at": datetime.now(UTC).isoformat(),
    }
