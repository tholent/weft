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

"""High-level notification dispatch helpers.

These functions are called from routers after a triggering action (update
created, reply relayed, member invited) and fan-out notifications to the
appropriate members.

All dispatches are best-effort: errors are logged and do not propagate
to the caller.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import get_settings
from app.models.attachment import Attachment
from app.models.enums import NotificationChannel, NotificationTrigger
from app.models.member import Member, MemberCircleHistory
from app.models.topic import Topic
from app.services.notifications.registry import ProviderRegistry
from app.services.notifications.service import NotificationService
from app.services.notifications.sms_format import (
    format_invite_sms,
    format_relay_sms,
    format_update_sms,
)

logger = logging.getLogger(__name__)


def _get_service(registry: ProviderRegistry) -> NotificationService:
    return NotificationService(registry)


async def _get_topic(session: AsyncSession, topic_id: uuid.UUID) -> Topic | None:
    result = await session.execute(select(Topic).where(Topic.id == topic_id))
    return result.scalar_one_or_none()


async def _get_member(session: AsyncSession, member_id: uuid.UUID) -> Member | None:
    result = await session.execute(select(Member).where(Member.id == member_id))
    return result.scalar_one_or_none()


async def _get_attachment_links(
    session: AsyncSession,
    topic_id: uuid.UUID,
    update_id: uuid.UUID,
) -> list[str]:
    """Return public URLs for all attachments on an update."""
    settings = get_settings()
    result = await session.execute(
        select(Attachment)
        .where(
            Attachment.update_id == update_id,
            Attachment.topic_id == topic_id,
        )
        .order_by(Attachment.created_at)
    )
    attachments = list(result.scalars().all())
    base = settings.base_url.rstrip("/")
    return [f"{base}/api/topics/{topic_id}/attachments/{att.id}" for att in attachments]


async def dispatch_update_notifications(
    session: AsyncSession,
    registry: ProviderRegistry,
    topic_id: uuid.UUID,
    update_id: uuid.UUID,
    circle_ids: list[uuid.UUID],
    author_handle: str | None,
    body: str,
) -> None:
    """Fan-out new-update notifications to members of the targeted circles.

    Skips the author. Members without a contact address are silently skipped.

    Attachments are included based on topic.photo_link_only:
    - False: attachment links appended inline to the message body
    - True: attachment links are included as links only (same effect over plain text/SMS)
    """
    topic = await _get_topic(session, topic_id)
    if topic is None:
        logger.warning("dispatch_update_notifications: topic %s not found", topic_id)
        return

    short_code = topic.short_code or ""
    email_subject = f"[{topic.default_title}] New update"

    # Load attachment links for this update
    attachment_links = await _get_attachment_links(session, topic_id, update_id)

    # Build email body with attachments
    email_body = body
    if attachment_links:
        if topic.photo_link_only:
            # Link-only: append links as text
            links_text = "\n".join(attachment_links)
            email_body = f"{body}\n\nAttachments:\n{links_text}"
        else:
            # Inline: also append links (plain-text email; HTML would embed images)
            links_text = "\n".join(attachment_links)
            email_body = f"{body}\n\nAttachments:\n{links_text}"

    # Build SMS body with attachments
    sms_body = format_update_sms(topic.default_title, short_code, author_handle, body)
    if attachment_links:
        if topic.photo_link_only:
            # Link-only mode: append first link to SMS body
            sms_body = f"{sms_body} {attachment_links[0]}"
        else:
            # MMS mode: append media URLs to the SMS body text
            sms_body = f"{sms_body} " + " ".join(attachment_links)

    # Collect unique members in the targeted circles
    result = await session.execute(
        select(Member)
        .join(MemberCircleHistory, Member.id == MemberCircleHistory.member_id)
        .where(
            MemberCircleHistory.circle_id.in_(circle_ids),  # type: ignore[union-attr]
            MemberCircleHistory.revoked_at.is_(None),  # type: ignore[union-attr]
        )
        .distinct()
    )
    members = list(result.scalars().all())

    service = _get_service(registry)
    for member in members:
        address = (
            member.email
            if member.notification_channel == NotificationChannel.email
            else member.phone
        )
        if not address:
            continue

        try:
            await service.dispatch(
                session=session,
                member_id=member.id,
                topic_id=topic_id,
                trigger=NotificationTrigger.new_update,
                subject=email_subject,
                body=(
                    sms_body
                    if member.notification_channel == NotificationChannel.sms
                    else email_body
                ),
                html_body=None,
                recipient_address=address,
                channel=member.notification_channel,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to dispatch update notification to member %s", member.id)


async def dispatch_relay_notifications(
    session: AsyncSession,
    registry: ProviderRegistry,
    topic_id: uuid.UUID,
    reply_id: uuid.UUID,
    circle_ids: list[uuid.UUID] | None,
    author_identity: str,
    reply_body: str,
) -> None:
    """Fan-out relay notifications to members of the relay target circles.

    ``circle_ids=None`` means all circles in the topic.
    """
    topic = await _get_topic(session, topic_id)
    if topic is None:
        logger.warning("dispatch_relay_notifications: topic %s not found", topic_id)
        return

    short_code = topic.short_code or ""
    sms_body = format_relay_sms(topic.default_title, short_code, author_identity, reply_body)
    email_subject = f"[{topic.default_title}] A reply was shared"

    if circle_ids is None:
        # All active members in the topic
        result = await session.execute(select(Member).where(Member.topic_id == topic_id))
        members = list(result.scalars().all())
    else:
        result = await session.execute(
            select(Member)
            .join(MemberCircleHistory, Member.id == MemberCircleHistory.member_id)
            .where(
                MemberCircleHistory.circle_id.in_(circle_ids),  # type: ignore[union-attr]
                MemberCircleHistory.revoked_at.is_(None),  # type: ignore[union-attr]
            )
            .distinct()
        )
        members = list(result.scalars().all())

    service = _get_service(registry)
    for member in members:
        address = (
            member.email
            if member.notification_channel == NotificationChannel.email
            else member.phone
        )
        if not address:
            continue

        try:
            await service.dispatch(
                session=session,
                member_id=member.id,
                topic_id=topic_id,
                trigger=NotificationTrigger.relay,
                subject=email_subject,
                body=(
                    sms_body
                    if member.notification_channel == NotificationChannel.sms
                    else reply_body
                ),
                html_body=None,
                recipient_address=address,
                channel=member.notification_channel,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to dispatch relay notification to member %s", member.id)


async def dispatch_invite_notification(
    session: AsyncSession,
    registry: ProviderRegistry,
    topic_id: uuid.UUID,
    member_id: uuid.UUID,
    magic_link: str,
) -> None:
    """Send an invite notification to a newly invited member."""
    topic = await _get_topic(session, topic_id)
    if topic is None:
        logger.warning("dispatch_invite_notification: topic %s not found", topic_id)
        return

    member = await _get_member(session, member_id)
    if member is None:
        logger.warning("dispatch_invite_notification: member %s not found", member_id)
        return

    address = (
        member.email if member.notification_channel == NotificationChannel.email else member.phone
    )
    if not address:
        return

    sms_body = format_invite_sms(topic.default_title, magic_link)
    email_subject = f'You\'ve been invited to follow "{topic.default_title}"'
    email_body = (
        f'You\'ve been invited to follow "{topic.default_title}".\n\nView updates: {magic_link}'
    )

    service = _get_service(registry)
    try:
        await service.dispatch(
            session=session,
            member_id=member.id,
            topic_id=topic_id,
            trigger=NotificationTrigger.invite,
            subject=email_subject,
            body=(
                sms_body if member.notification_channel == NotificationChannel.sms else email_body
            ),
            html_body=None,
            recipient_address=address,
            channel=member.notification_channel,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to dispatch invite notification to member %s", member_id)
