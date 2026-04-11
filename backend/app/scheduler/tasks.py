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

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.config import Settings, get_settings
from app.db.session import async_session_factory
from app.models.enums import (
    DeliveryMode,
    MemberRole,
    NotificationChannel,
    NotificationStatus,
    TopicStatus,
    TransferStatus,
)
from app.models.member import Member
from app.models.notification import NotificationLog, NotificationPreference
from app.models.token import Token
from app.models.topic import Topic
from app.models.transfer import CreatorTransfer
from app.services.notifications.registry import ProviderRegistry, create_registry
from app.services.purge import purge_emails
from app.services.transfer import execute_transfer

logger = logging.getLogger(__name__)


async def auto_archive_task() -> None:
    """Archive topics with no activity in the configured number of days."""
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(days=settings.auto_archive_days)

    async with async_session_factory() as session:
        result = await session.execute(
            select(Topic).where(
                Topic.status == TopicStatus.active,
            )
        )
        topics = result.scalars().all()

        for topic in topics:
            # Check if any token has been used recently
            token_result = await session.execute(
                select(Token)
                .join(Member, col(Token.member_id) == col(Member.id))
                .where(
                    Member.topic_id == topic.id,
                    col(Token.last_used_at).is_not(None),
                    col(Token.last_used_at) > cutoff,
                )
            )
            if token_result.scalars().first() is not None:
                continue

            logger.info("Auto-archiving topic %s", topic.id)
            topic.status = TopicStatus.archived
            topic.closed_at = datetime.now(UTC)
            session.add(topic)
            await purge_emails(session, topic.id)

        await session.commit()


async def transfer_deadline_task() -> None:
    """Execute transfers past their deadline where creator has not authenticated."""
    async with async_session_factory() as session:
        now = datetime.now(UTC)
        result = await session.execute(
            select(CreatorTransfer).where(
                CreatorTransfer.status == TransferStatus.pending,
                CreatorTransfer.deadline <= now,
            )
        )
        transfers = result.scalars().all()

        for transfer in transfers:
            # Check if creator has been active since transfer was requested
            creator_result = await session.execute(
                select(Member).where(
                    Member.topic_id == transfer.topic_id,
                    Member.role == MemberRole.owner,
                )
            )
            creator = creator_result.scalar_one_or_none()
            if creator is None:
                continue

            active_token_result = await session.execute(
                select(Token).where(
                    Token.member_id == creator.id,
                    col(Token.last_used_at).is_not(None),
                    col(Token.last_used_at) > transfer.created_at,
                )
            )
            if active_token_result.scalars().first() is not None:
                # Creator was active, cancel transfer
                transfer.status = TransferStatus.denied
                transfer.resolved_at = now
                session.add(transfer)
                continue

            logger.info("Executing transfer %s for topic %s", transfer.id, transfer.topic_id)
            try:
                await execute_transfer(session, transfer.id)
            except ValueError as e:
                logger.error("Failed to execute transfer %s: %s", transfer.id, e)

        await session.commit()


# ---------------------------------------------------------------------------
# Digest notification helpers
# ---------------------------------------------------------------------------


def _build_digest_message(
    member: Member,
    topic_title: str,
    short_code: str,
    count: int,
    settings: Settings,
) -> tuple[str, str]:
    """Return (subject, body) for a digest notification."""
    if member.notification_channel == NotificationChannel.sms:
        from app.services.notifications.sms_format import format_digest_sms

        link = f"{settings.base_url}/topic"
        body = format_digest_sms(topic_title, short_code, count, link)
        subject = f"[{topic_title}] Digest"
    else:
        noun = "update" if count == 1 else "updates"
        subject = f"[{topic_title}] Digest: {count} new {noun}"
        body = (
            f'You have {count} new {noun} in "{topic_title}".\n\n'
            f"View updates at {settings.base_url}/topic"
        )
    return subject, body


async def _mark_logs(
    session: AsyncSession,
    logs: list[NotificationLog],
    status: NotificationStatus,
    now: datetime,
    *,
    message_id: str | None = None,
    error_detail: str | None = None,
) -> None:
    """Update a batch of notification logs with the given status."""
    for log in logs:
        log.status = status
        log.sent_at = now
        if message_id is not None:
            log.provider_message_id = message_id
        if error_detail is not None:
            log.error_detail = error_detail
        session.add(log)


async def _send_topic_digest(
    session: AsyncSession,
    member: Member,
    topic_logs: list[NotificationLog],
    registry: ProviderRegistry,
    settings: Settings,
) -> None:
    """Send a digest for one member/topic combination and update the log rows."""
    from uuid import UUID

    topic_id: UUID = topic_logs[0].topic_id
    topic_result = await session.execute(select(Topic).where(Topic.id == topic_id))
    topic = topic_result.scalar_one_or_none()

    count = len(topic_logs)
    topic_title = topic.default_title if topic else str(topic_id)
    short_code = (topic.short_code or "") if topic else ""

    subject, body = _build_digest_message(member, topic_title, short_code, count, settings)

    provider = registry.get(member.notification_channel)
    now = datetime.now(UTC)

    if provider is None:
        logger.warning(
            "No provider for channel %s; skipping digest for member %s",
            member.notification_channel,
            member.id,
        )
        await _mark_logs(session, topic_logs, NotificationStatus.skipped, now)
        return

    recipient = (
        member.email if member.notification_channel == NotificationChannel.email else member.phone
    )
    if recipient is None:
        logger.warning(
            "Skipping digest for member %s: no contact address for channel %s",
            member.id,
            member.notification_channel,
        )
        await _mark_logs(session, topic_logs, NotificationStatus.skipped, now)
        return

    try:
        message_id = await provider.send(
            recipient=recipient,
            subject=subject,
            body=body,
        )
        await _mark_logs(session, topic_logs, NotificationStatus.sent, now, message_id=message_id)
        logger.info("Sent digest to member %s (%d notifications)", member.id, count)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send digest to member %s: %s", member.id, exc)
        await _mark_logs(
            session, topic_logs, NotificationStatus.failed, now, error_detail=str(exc)
        )


async def _process_member_digest(
    session: AsyncSession,
    member_id: uuid.UUID,
    registry: ProviderRegistry,
    settings: Settings,
) -> None:
    """Process all pending digest logs for a single member."""
    log_result = await session.execute(
        select(NotificationLog).where(
            NotificationLog.member_id == member_id,
            NotificationLog.status == NotificationStatus.pending_digest,
        )
    )
    pending_logs = list(log_result.scalars().all())
    if not pending_logs:
        return

    member_result = await session.execute(select(Member).where(Member.id == member_id))
    member = member_result.scalar_one_or_none()
    if member is None:
        return

    address = (
        member.email if member.notification_channel == NotificationChannel.email else member.phone
    )
    if not address:
        # No contact address; mark logs skipped to avoid reprocessing
        now = datetime.now(UTC)
        await _mark_logs(session, pending_logs, NotificationStatus.skipped, now)
        return

    # Group by topic so each topic gets its own digest message
    topic_ids = list({log.topic_id for log in pending_logs})
    for topic_id in topic_ids:
        topic_logs = [lg for lg in pending_logs if lg.topic_id == topic_id]
        await _send_topic_digest(session, member, topic_logs, registry, settings)


async def digest_notification_task() -> None:
    """Batch pending digest notifications and send them per member.

    Runs every hour.  For each member that has any digest-mode preference,
    find their pending (status=pending_digest) NotificationLog rows, aggregate
    them into a single digest message, send it, and mark the logs sent.
    """
    settings = get_settings()
    registry = create_registry(settings)

    async with async_session_factory() as session:
        # Find members who have at least one digest-mode preference
        pref_result = await session.execute(
            select(NotificationPreference.member_id)
            .where(NotificationPreference.delivery_mode == DeliveryMode.digest)
            .distinct()
        )
        member_ids = list(pref_result.scalars().all())

        if not member_ids:
            return

        for member_id in member_ids:
            await _process_member_digest(session, member_id, registry, settings)

        await session.commit()
