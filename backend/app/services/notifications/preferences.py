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

from app.models.enums import DeliveryMode, NotificationChannel, NotificationTrigger
from app.models.notification import NotificationPreference


async def get_preferences(
    session: AsyncSession, member_id: uuid.UUID
) -> list[NotificationPreference]:
    """Return all notification preferences for a member."""
    result = await session.execute(
        select(NotificationPreference).where(NotificationPreference.member_id == member_id)
    )
    return list(result.scalars().all())


async def get_preference(
    session: AsyncSession,
    member_id: uuid.UUID,
    trigger: NotificationTrigger,
) -> NotificationPreference | None:
    """Return a single preference for a member and trigger, or None if not set."""
    result = await session.execute(
        select(NotificationPreference).where(
            NotificationPreference.member_id == member_id,
            NotificationPreference.trigger == trigger,
        )
    )
    return result.scalar_one_or_none()


async def update_preference(
    session: AsyncSession,
    member_id: uuid.UUID,
    trigger: NotificationTrigger,
    channel: NotificationChannel,
    delivery_mode: DeliveryMode,
) -> NotificationPreference:
    """Create or update a notification preference for a member/trigger pair."""
    pref = await get_preference(session, member_id, trigger)
    if pref is None:
        pref = NotificationPreference(
            member_id=member_id,
            channel=channel,
            trigger=trigger,
            delivery_mode=delivery_mode,
        )
    else:
        pref.channel = channel
        pref.delivery_mode = delivery_mode
    session.add(pref)
    await session.flush()
    return pref


async def create_defaults(
    session: AsyncSession,
    member_id: uuid.UUID,
    channel: NotificationChannel,
) -> list[NotificationPreference]:
    """Create default notification preferences for all triggers for a new member.

    Defaults: immediate delivery for all triggers on the member's chosen channel.
    """
    prefs: list[NotificationPreference] = []
    for trigger in NotificationTrigger:
        pref = NotificationPreference(
            member_id=member_id,
            channel=channel,
            trigger=trigger,
            delivery_mode=DeliveryMode.immediate,
        )
        session.add(pref)
        prefs.append(pref)
    await session.flush()
    return prefs
