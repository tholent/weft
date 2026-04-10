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
from datetime import UTC, datetime, timedelta

from sqlmodel import select

from app.config import get_settings
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
from app.services.notifications.registry import create_registry
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
            result = await session.execute(
                select(Token)
                .join(Member, Token.member_id == Member.id)
                .where(
                    Member.topic_id == topic.id,
                    Token.last_used_at.is_not(None),  # type: ignore[union-attr]
                    Token.last_used_at > cutoff,
                )
            )
            if result.scalars().first() is not None:
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
            result = await session.execute(
                select(Member).where(
                    Member.topic_id == transfer.topic_id,
                    Member.role == MemberRole.owner,
                )
            )
            creator = result.scalar_one_or_none()
            if creator is None:
                continue

            result = await session.execute(
                select(Token).where(
                    Token.member_id == creator.id,
                    Token.last_used_at.is_not(None),  # type: ignore[union-attr]
                    Token.last_used_at > transfer.created_at,
                )
            )
            if result.scalars().first() is not None:
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


async def digest_notification_task() -> None:
    """Batch pending digest notifications and send them per member.

    Runs every hour.  For each member that has any digest-mode preference,
    find their pending (status=pending) NotificationLog rows, aggregate
    them into a single digest message, send it, and mark the logs sent.
    """
    settings = get_settings()
    registry = create_registry(settings)

    async with async_session_factory() as session:
        # Find members who have at least one digest-mode preference
        pref_result = await session.execute(
            select(NotificationPreference.member_id).where(
                NotificationPreference.delivery_mode == DeliveryMode.digest
            ).distinct()
        )
        member_ids = list(pref_result.scalars().all())

        if not member_ids:
            return

        for member_id in member_ids:
            # Load pending log entries for this member
            log_result = await session.execute(
                select(NotificationLog).where(
                    NotificationLog.member_id == member_id,
                    NotificationLog.status == NotificationStatus.pending,
                )
            )
            pending_logs = list(log_result.scalars().all())
            if not pending_logs:
                continue

            # Load member contact info
            member_result = await session.execute(
                select(Member).where(Member.id == member_id)
            )
            member = member_result.scalar_one_or_none()
            if member is None:
                continue

            address = (
                member.email
                if member.notification_channel == NotificationChannel.email
                else member.phone
            )
            if not address:
                # No contact address; mark logs skipped to avoid reprocessing
                for log in pending_logs:
                    log.status = NotificationStatus.skipped
                    log.sent_at = datetime.now(UTC)
                    session.add(log)
                continue

            # Group by topic so each topic gets its own digest message
            topic_ids = list({log.topic_id for log in pending_logs})
            for topic_id in topic_ids:
                topic_logs = [lg for lg in pending_logs if lg.topic_id == topic_id]

                topic_result = await session.execute(
                    select(Topic).where(Topic.id == topic_id)
                )
                topic = topic_result.scalar_one_or_none()

                count = len(topic_logs)
                topic_title = topic.default_title if topic else str(topic_id)
                short_code = (topic.short_code or "") if topic else ""

                if member.notification_channel == NotificationChannel.sms:
                    from app.services.notifications.sms_format import format_digest_sms

                    base_url = settings.base_url
                    link = f"{base_url}/topic"
                    body = format_digest_sms(topic_title, short_code, count, link)
                    subject = f"[{topic_title}] Digest"
                else:
                    noun = "update" if count == 1 else "updates"
                    subject = f"[{topic_title}] Digest: {count} new {noun}"
                    body = (
                        f"You have {count} new {noun} in \"{topic_title}\".\n\n"
                        f"View updates at {settings.base_url}/topic"
                    )

                provider = registry.get(member.notification_channel)
                now = datetime.now(UTC)

                if provider is None:
                    logger.warning(
                        "No provider for channel %s; skipping digest for member %s",
                        member.notification_channel,
                        member_id,
                    )
                    for log in topic_logs:
                        log.status = NotificationStatus.skipped
                        log.sent_at = now
                        session.add(log)
                    continue

                try:
                    message_id = await provider.send(
                        recipient=address,
                        subject=subject,
                        body=body,
                    )
                    for log in topic_logs:
                        log.status = NotificationStatus.sent
                        log.provider_message_id = message_id
                        log.sent_at = now
                        session.add(log)
                    logger.info(
                        "Sent digest to member %s (%d notifications)",
                        member_id,
                        count,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "Failed to send digest to member %s: %s", member_id, exc
                    )
                    for log in topic_logs:
                        log.status = NotificationStatus.failed
                        log.error_detail = str(exc)
                        session.add(log)

        await session.commit()
