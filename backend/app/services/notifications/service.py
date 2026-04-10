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

"""Notification dispatch service.

Resolves member preferences and dispatches notifications via the
appropriate provider from the registry.
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    DeliveryMode,
    NotificationChannel,
    NotificationStatus,
    NotificationTrigger,
)
from app.models.notification import NotificationLog, NotificationPreference
from app.services.notifications.preferences import get_preference
from app.services.notifications.registry import ProviderRegistry

logger = logging.getLogger(__name__)


class NotificationService:
    """Dispatches notifications to members based on their preferences."""

    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry

    async def dispatch(
        self,
        *,
        session: AsyncSession,
        member_id: uuid.UUID,
        topic_id: uuid.UUID,
        trigger: NotificationTrigger,
        subject: str,
        body: str,
        html_body: str | None = None,
        recipient_address: str,
        channel: NotificationChannel,
    ) -> NotificationLog:
        """Dispatch a notification to a single member.

        Checks the member's preference for this trigger. If the mode is
        ``muted``, records a skipped log entry and returns early. For
        ``digest`` mode, also records a skipped entry (digest delivery
        is handled separately by the scheduler). For ``immediate``,
        sends via the registered provider.

        Returns the persisted ``NotificationLog`` row.
        """
        pref: NotificationPreference | None = await get_preference(session, member_id, trigger)

        # Default: immediate on the member's channel if no preference recorded
        delivery_mode = pref.delivery_mode if pref else DeliveryMode.immediate
        effective_channel = pref.channel if pref else channel

        log = NotificationLog(
            member_id=member_id,
            topic_id=topic_id,
            channel=effective_channel,
            trigger=trigger,
            status=NotificationStatus.pending,
        )
        session.add(log)
        await session.flush()

        if delivery_mode == DeliveryMode.muted:
            log.status = NotificationStatus.skipped
            await session.flush()
            return log

        if delivery_mode == DeliveryMode.digest:
            # Digest messages are batched; mark as skipped here (scheduler handles them).
            log.status = NotificationStatus.skipped
            await session.flush()
            return log

        # Immediate delivery
        provider = self._registry.get(effective_channel)
        if provider is None:
            logger.warning(
                "No provider registered for channel %s; skipping notification for member %s",
                effective_channel,
                member_id,
            )
            log.status = NotificationStatus.skipped
            await session.flush()
            return log

        try:
            message_id = await provider.send(
                recipient=recipient_address,
                subject=subject,
                body=body,
                html_body=html_body,
            )
            log.status = NotificationStatus.sent
            log.provider_message_id = message_id
            log.sent_at = datetime.now(UTC)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to send %s notification to member %s: %s",
                effective_channel,
                member_id,
                exc,
            )
            log.status = NotificationStatus.failed
            log.error_detail = str(exc)

        await session.flush()
        return log
