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
from sqlmodel import col, select

from app.models.attachment import Attachment
from app.models.circle import Circle
from app.models.member import Member
from app.models.reply import ModResponse, Relay, Reply
from app.models.topic import Topic
from app.models.update import Update, UpdateCircle

# ---------------------------------------------------------------------------
# Phase helpers
# ---------------------------------------------------------------------------


async def _load_topic(session: AsyncSession, topic_id: uuid.UUID) -> Topic:
    result = await session.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()
    if topic is None:
        raise ValueError(f"Topic {topic_id} not found")
    return topic


async def _load_circles(
    session: AsyncSession, topic_id: uuid.UUID
) -> tuple[list[Circle], dict[uuid.UUID, Circle]]:
    result = await session.execute(select(Circle).where(Circle.topic_id == topic_id))
    circles = list(result.scalars().all())
    circle_map: dict[uuid.UUID, Circle] = {c.id: c for c in circles}
    return circles, circle_map


async def _load_member_map(
    session: AsyncSession, topic_id: uuid.UUID
) -> dict[uuid.UUID, str | None]:
    result = await session.execute(select(Member).where(Member.topic_id == topic_id))
    return {m.id: m.display_handle for m in result.scalars().all()}


async def _load_updates(session: AsyncSession, topic_id: uuid.UUID) -> list[Update]:
    result = await session.execute(
        select(Update)
        .where(Update.topic_id == topic_id, col(Update.deleted_at).is_(None))
        .order_by(col(Update.created_at))
    )
    return list(result.scalars().all())


async def _load_update_circles(
    session: AsyncSession,
    update_ids: list[uuid.UUID],
    circle_map: dict[uuid.UUID, Circle],
) -> dict[uuid.UUID, list[str]]:
    if not update_ids:
        return {}
    result = await session.execute(
        select(UpdateCircle).where(col(UpdateCircle.update_id).in_(update_ids))
    )
    mapping: dict[uuid.UUID, list[str]] = {}
    for uc in result.scalars().all():
        circle = circle_map.get(uc.circle_id)
        circle_name = circle.name if circle else str(uc.circle_id)
        mapping.setdefault(uc.update_id, []).append(circle_name)
    return mapping


async def _load_update_attachments(
    session: AsyncSession, update_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[dict[str, Any]]]:
    if not update_ids:
        return {}
    result = await session.execute(
        select(Attachment).where(col(Attachment.update_id).in_(update_ids))
    )
    mapping: dict[uuid.UUID, list[dict[str, Any]]] = {}
    for att in result.scalars().all():
        mapping.setdefault(att.update_id, []).append(
            {
                "filename": att.filename,
                "content_type": att.content_type,
                "size_bytes": att.size_bytes,
                # storage_key is intentionally excluded — it is an internal
                # infrastructure detail and must never appear in exports.
            }
        )
    return mapping


async def _load_replies(session: AsyncSession, update_ids: list[uuid.UUID]) -> list[Reply]:
    if not update_ids:
        return []
    result = await session.execute(
        select(Reply).where(col(Reply.update_id).in_(update_ids)).order_by(col(Reply.created_at))
    )
    return list(result.scalars().all())


async def _load_mod_responses(
    session: AsyncSession, reply_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[dict[str, Any]]]:
    if not reply_ids:
        return {}
    result = await session.execute(
        select(ModResponse)
        .where(col(ModResponse.reply_id).in_(reply_ids))
        .order_by(col(ModResponse.created_at))
    )
    mapping: dict[uuid.UUID, list[dict[str, Any]]] = {}
    for mr in result.scalars().all():
        mapping.setdefault(mr.reply_id, []).append(
            {
                "body": mr.body,
                "author": None,  # filled in by caller with member_map
                "_author_member_id": mr.author_member_id,
                "scope": str(mr.scope),
                "created_at": mr.created_at.isoformat(),
            }
        )
    return mapping


async def _load_relays(
    session: AsyncSession,
    reply_ids: list[uuid.UUID],
    member_map: dict[uuid.UUID, str | None],
    circle_map: dict[uuid.UUID, Circle],
) -> list[dict[str, Any]]:
    if not reply_ids:
        return []
    result = await session.execute(
        select(Relay).where(col(Relay.reply_id).in_(reply_ids)).order_by(col(Relay.relayed_at))
    )
    return [
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
        for relay in result.scalars().all()
    ]


def _build_update_replies(
    replies: list[Reply],
    member_map: dict[uuid.UUID, str | None],
    mod_responses_raw: dict[uuid.UUID, list[dict[str, Any]]],
) -> dict[uuid.UUID, list[dict[str, Any]]]:
    """Group replies by update_id, resolving author handles and mod responses."""
    # Resolve author in mod responses
    mod_responses: dict[uuid.UUID, list[dict[str, Any]]] = {}
    for reply_id, entries in mod_responses_raw.items():
        resolved = []
        for entry in entries:
            item = dict(entry)
            item["author"] = member_map.get(item.pop("_author_member_id"))
            resolved.append(item)
        mod_responses[reply_id] = resolved

    update_replies: dict[uuid.UUID, list[dict[str, Any]]] = {}
    for reply in replies:
        update_replies.setdefault(reply.update_id, []).append(
            {
                "body": reply.body,
                "author": member_map.get(reply.author_member_id),
                "wants_to_share": reply.wants_to_share,
                "relay_status": str(reply.relay_status),
                "created_at": reply.created_at.isoformat(),
                "mod_responses": mod_responses.get(reply.id, []),
            }
        )
    return update_replies


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def export_topic(session: AsyncSession, topic_id: uuid.UUID) -> dict[str, Any]:
    """Export full topic data as a structured dict (for JSON serialization).

    The export includes topic metadata, circles, updates with replies and
    attachments, and relays. It excludes all PII (emails, phones) and
    internal IDs other than those needed for structural linkage within the
    export itself.

    Raises:
        ValueError: If the topic is not found.
    """
    topic = await _load_topic(session, topic_id)
    circles, circle_map = await _load_circles(session, topic_id)
    member_map = await _load_member_map(session, topic_id)
    updates = await _load_updates(session, topic_id)

    update_ids = [u.id for u in updates]
    update_circles = await _load_update_circles(session, update_ids, circle_map)
    update_attachments = await _load_update_attachments(session, update_ids)

    replies = await _load_replies(session, update_ids)
    reply_ids = [r.id for r in replies]

    mod_responses_raw = await _load_mod_responses(session, reply_ids)
    update_replies = _build_update_replies(replies, member_map, mod_responses_raw)

    relays_export = await _load_relays(session, reply_ids, member_map, circle_map)

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
