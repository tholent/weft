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

# WARNING: This router must NEVER be mounted in production.
# It is gated on `settings.env == "test"` in `app/main.py`.
# Do not remove that guard.

from typing import Any
from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.session import get_session
from app.models.enums import MemberRole, NotificationChannel
from app.models.member import Member, MemberCircleHistory
from app.services.auth import create_magic_link, generate_token
from app.services.circle import create_circle
from app.services.member import invite_member
from app.services.notifications.preferences import create_defaults
from app.services.reply import create_reply
from app.services.topic import create_topic
from app.services.update import create_update

router = APIRouter(prefix="/test/seed", tags=["test-seed"])

# ---------------------------------------------------------------------------
# Spec models
# ---------------------------------------------------------------------------


class SeedMemberSpec(BaseModel):
    email: str
    role: MemberRole
    name: str | None = None


class SeedCircleSpec(BaseModel):
    name: str
    members: list[SeedMemberSpec] = []


class SeedUpdateSpec(BaseModel):
    body: str
    circle_names: list[str]  # names of circles this update targets
    author_email: str  # email of the member who posts it


class SeedReplySpec(BaseModel):
    update_index: int  # index into updates list
    author_email: str
    body: str


class SeedTopicSpec(BaseModel):
    title: str = "E2E Seed Topic"
    owner_email: str = "owner@example.com"
    owner_name: str = "Seed Owner"
    circles: list[SeedCircleSpec] = []
    updates: list[SeedUpdateSpec] = []
    replies: list[SeedReplySpec] = []


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _guard(settings: Settings) -> None:
    """Belt-and-suspenders runtime guard — reject non-test envs even if somehow mounted."""
    if settings.env != "test":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _extract_magic_token(member_id: str) -> str:
    """Return just the signed token portion from a magic link URL.

    create_magic_link returns a full URL like ``{base_url}/auth?t={signed}``.
    We extract the ``t`` query parameter so callers can construct their own URLs.
    """
    url = create_magic_link(str(member_id))
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    tokens = params.get("t", [])
    if not tokens:
        raise RuntimeError(f"create_magic_link returned unexpected URL: {url!r}")
    return tokens[0]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/reset")
async def reset_db(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, bool]:
    """Truncate all application tables. Only available when env == 'test'."""
    _guard(settings)

    # Delete in child-before-parent order to avoid FK violations.
    tables = [
        "mod_response",
        "relay",
        "reply",
        "attachment",
        "update_circle",
        "update",
        "notification_log",
        "notification_preference",
        "creator_transfer",
        "token",
        "member_circle_history",
        "member",
        "circle",
        "topic",
    ]
    for table in tables:
        await session.execute(text(f'DELETE FROM "{table}"'))  # noqa: S608
    await session.commit()
    return {"ok": True}


@router.post("/topic")
async def seed_topic(
    spec: SeedTopicSpec,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Create a topic from a spec and return raw tokens for all members."""
    _guard(settings)

    # --- Create topic + owner via service layer ---
    topic, owner_member, _magic_link = await create_topic(
        session,
        default_title=spec.title,
        creator_email=spec.owner_email,
    )

    # Generate a raw bearer token for the owner (create_topic returns a magic link,
    # not a bearer token — E2E tests need a raw bearer token directly).
    owner_raw_token = await generate_token(session, owner_member.id)
    owner_magic = _extract_magic_token(str(owner_member.id))

    # Maps for later use when creating updates/replies
    circle_map: dict[str, Any] = {}  # circle_name -> Circle object
    circle_ids: dict[str, str] = {}  # circle_name -> str(uuid)

    # Tokens bucketed by role
    admin_tokens: dict[str, str] = {}
    moderator_tokens: dict[str, str] = {}
    recipient_tokens: dict[str, str] = {}

    # Magic-link signed tokens bucketed by role
    admin_magic: dict[str, str] = {}
    moderator_magic: dict[str, str] = {}
    recipient_magic: dict[str, str] = {}

    # email -> member_id (for update/reply author resolution)
    member_id_by_email: dict[str, Any] = {spec.owner_email: owner_member.id}

    # --- Create circles and their members ---
    for circle_spec in spec.circles:
        circle = await create_circle(session, topic.id, circle_spec.name)
        circle_map[circle_spec.name] = circle
        circle_ids[circle_spec.name] = str(circle.id)

        for member_spec in circle_spec.members:
            if member_spec.role == MemberRole.owner:
                # Skip — a topic already has an owner; this would fail business rules.
                # TODO: support promoting the seeded owner's email if needed.
                continue

            if member_spec.role == MemberRole.admin:
                # invite_member only accepts recipient/moderator; admins must be
                # created directly and placed in the circle via history row.
                admin_member = Member(
                    topic_id=topic.id,
                    role=MemberRole.admin,
                    email=member_spec.email,
                    notification_channel=NotificationChannel.email,
                )
                session.add(admin_member)
                await session.flush()
                history = MemberCircleHistory(member_id=admin_member.id, circle_id=circle.id)
                session.add(history)
                await create_defaults(session, admin_member.id, NotificationChannel.email)
                raw_token = await generate_token(session, admin_member.id)
                member_id_by_email[member_spec.email] = admin_member.id
                admin_tokens[member_spec.email] = raw_token
                admin_magic[member_spec.email] = _extract_magic_token(str(admin_member.id))
            else:
                member, raw_token = await invite_member(
                    session,
                    topic_id=topic.id,
                    circle_id=circle.id,
                    role=member_spec.role,
                    email=member_spec.email,
                )
                member_id_by_email[member_spec.email] = member.id

                if member_spec.role == MemberRole.moderator:
                    moderator_tokens[member_spec.email] = raw_token
                    moderator_magic[member_spec.email] = _extract_magic_token(str(member.id))
                else:
                    recipient_tokens[member_spec.email] = raw_token
                    recipient_magic[member_spec.email] = _extract_magic_token(str(member.id))

    # --- Create updates ---
    created_updates = []
    for update_spec in spec.updates:
        author_id = member_id_by_email.get(update_spec.author_email)
        if author_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Author email not found: {update_spec.author_email}",
            )
        target_circle_ids = []
        for cname in update_spec.circle_names:
            c = circle_map.get(cname)
            if c is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Circle not found: {cname}",
                )
            target_circle_ids.append(c.id)

        update = await create_update(
            session,
            topic_id=topic.id,
            author_member_id=author_id,
            body=update_spec.body,
            circle_ids=target_circle_ids,
        )
        created_updates.append(update)

    # --- Create replies ---
    for reply_spec in spec.replies:
        idx = reply_spec.update_index
        if idx < 0 or idx >= len(created_updates):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"update_index {idx} out of range (have {len(created_updates)} updates)",
            )
        author_id = member_id_by_email.get(reply_spec.author_email)
        if author_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Author email not found: {reply_spec.author_email}",
            )
        await create_reply(
            session,
            update_id=created_updates[idx].id,
            author_member_id=author_id,
            body=reply_spec.body,
        )

    await session.commit()

    return {
        "topic_id": str(topic.id),
        "owner_token": owner_raw_token,
        "admin_tokens": admin_tokens,
        "moderator_tokens": moderator_tokens,
        "recipient_tokens": recipient_tokens,
        "circle_ids": circle_ids,
        "magic_links": {
            "owner": owner_magic,
            "admins": admin_magic,
            "moderators": moderator_magic,
            "recipients": recipient_magic,
        },
    }
