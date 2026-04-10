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

"""Inbound SMS webhook router.

Handles POST callbacks from Twilio (and Twilio-compatible providers) for
inbound SMS messages.  The webhook normalises the incoming payload and
routes it to the SMS command processor.

For simplicity, this endpoint returns a plain 200 response — providers
expect a fast acknowledgement.  Any work that needs a reply SMS is logged
and handled asynchronously by the command processor.
"""

import logging

from fastapi import APIRouter, Depends, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.notifications.sms_commands import SmsCommand, parse_sms_command

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/sms", tags=["sms"])


@router.post("/inbound")
async def sms_inbound(
    From: str = Form(...),
    Body: str = Form(...),
    To: str = Form(default=""),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Handle an inbound SMS message from the provider webhook.

    Twilio sends ``From``, ``To``, and ``Body`` as form fields in the
    POST body.  We parse the body for recognised commands and dispatch
    accordingly.

    Currently handles:
    - ``STOP`` / ``MUTE`` — mute all notifications for the sender
    - ``RESUME`` — re-enable immediate delivery for the sender
    - ``LIST`` — (reserved, not yet implemented)

    Non-command messages are logged but not yet routed (Wave 5: task 36).
    """
    phone_number = From.strip()
    message_body = Body.strip()

    command = parse_sms_command(message_body)

    if command is None:
        logger.info(
            "Received non-command SMS from %s (to %s): %r",
            phone_number,
            To,
            message_body[:80],
        )
        # Non-command reply routing is handled in Wave 5 (task 36).
        return {"status": "accepted"}

    logger.info("Received SMS command %r from %s", command, phone_number)

    if command in (SmsCommand.stop, SmsCommand.mute):
        await _handle_stop(session, phone_number)
    elif command == SmsCommand.resume:
        await _handle_resume(session, phone_number)
    elif command == SmsCommand.list:
        # LIST response is a Wave 5 enhancement; acknowledge for now.
        logger.info("LIST command from %s acknowledged (not yet implemented)", phone_number)

    return {"status": "accepted"}


async def _handle_stop(session: AsyncSession, phone_number: str) -> None:
    """Mute all notification triggers for the member with *phone_number*."""
    from sqlmodel import select

    from app.models.enums import DeliveryMode, NotificationTrigger
    from app.models.member import Member
    from app.models.notification import NotificationPreference

    result = await session.execute(
        select(Member).where(Member.phone == phone_number)
    )
    members = list(result.scalars().all())

    if not members:
        logger.warning("STOP from unknown phone %s — no member found", phone_number)
        return

    for member in members:
        for trigger in NotificationTrigger:
            pref_result = await session.execute(
                select(NotificationPreference).where(
                    NotificationPreference.member_id == member.id,
                    NotificationPreference.trigger == trigger,
                )
            )
            pref = pref_result.scalar_one_or_none()
            if pref is None:
                pref = NotificationPreference(
                    member_id=member.id,
                    channel=member.notification_channel,
                    trigger=trigger,
                    delivery_mode=DeliveryMode.muted,
                )
            else:
                pref.delivery_mode = DeliveryMode.muted
            session.add(pref)

    await session.flush()
    logger.info("Muted all notifications for phone %s (%d member(s))", phone_number, len(members))


async def _handle_resume(session: AsyncSession, phone_number: str) -> None:
    """Re-enable immediate delivery on all triggers for *phone_number*."""
    from sqlmodel import select

    from app.models.enums import DeliveryMode, NotificationTrigger
    from app.models.member import Member
    from app.models.notification import NotificationPreference

    result = await session.execute(
        select(Member).where(Member.phone == phone_number)
    )
    members = list(result.scalars().all())

    if not members:
        logger.warning("RESUME from unknown phone %s — no member found", phone_number)
        return

    for member in members:
        for trigger in NotificationTrigger:
            pref_result = await session.execute(
                select(NotificationPreference).where(
                    NotificationPreference.member_id == member.id,
                    NotificationPreference.trigger == trigger,
                )
            )
            pref = pref_result.scalar_one_or_none()
            if pref is None:
                pref = NotificationPreference(
                    member_id=member.id,
                    channel=member.notification_channel,
                    trigger=trigger,
                    delivery_mode=DeliveryMode.immediate,
                )
            else:
                pref.delivery_mode = DeliveryMode.immediate
            session.add(pref)

    await session.flush()
    logger.info(
        "Resumed immediate delivery for phone %s (%d member(s))", phone_number, len(members)
    )
