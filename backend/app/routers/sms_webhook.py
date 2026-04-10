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
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import SessionDep
from app.deps_sms import verify_twilio_signature
from app.rate_limit import limiter
from app.services.notifications.log_safe import hash_for_log
from app.services.notifications.sms_commands import SmsCommand, parse_sms_command

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/sms", tags=["sms"])


@router.post("/inbound", dependencies=[Depends(verify_twilio_signature)])
@limiter.limit("60/minute")
async def sms_inbound(
    request: Request,
    from_number: Annotated[str, Form(alias="From")],
    body: Annotated[str, Form(alias="Body")],
    session: SessionDep,
    to_number: Annotated[str, Form(alias="To")] = "",
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
    phone_number = from_number.strip()
    message_body = body.strip()

    command = parse_sms_command(message_body)

    if command is None:
        logger.info(
            "Received non-command SMS from phone_hash=%s to_hash=%s body_len=%d",
            hash_for_log(phone_number),
            hash_for_log(to_number),
            len(message_body),
        )
        # Non-command reply routing is handled in Wave 5 (task 36).
        return {"status": "accepted"}

    logger.info(
        "Received SMS command %r from phone_hash=%s",
        command,
        hash_for_log(phone_number),
    )

    if command in (SmsCommand.stop, SmsCommand.mute):
        await _handle_stop(session, phone_number)
    elif command == SmsCommand.resume:
        await _handle_resume(session, phone_number)
    elif command == SmsCommand.list:
        # LIST response is a Wave 5 enhancement; acknowledge for now.
        logger.info(
            "LIST command from phone_hash=%s acknowledged (not yet implemented)",
            hash_for_log(phone_number),
        )

    return {"status": "accepted"}


async def _handle_stop(session: AsyncSession, phone_number: str) -> None:
    """Mute all notification triggers for the member with *phone_number*."""
    from sqlmodel import select

    from app.models.enums import DeliveryMode, NotificationTrigger
    from app.models.member import Member
    from app.models.notification import NotificationPreference

    result = await session.execute(select(Member).where(Member.phone == phone_number))
    members = list(result.scalars().all())

    if not members:
        logger.warning(
            "STOP from unknown phone phone_hash=%s — no member found",
            hash_for_log(phone_number),
        )
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
    logger.info(
        "Muted all notifications for phone_hash=%s (%d member(s))",
        hash_for_log(phone_number),
        len(members),
    )


async def _handle_resume(session: AsyncSession, phone_number: str) -> None:
    """Re-enable immediate delivery on all triggers for *phone_number*."""
    from sqlmodel import select

    from app.models.enums import DeliveryMode, NotificationTrigger
    from app.models.member import Member
    from app.models.notification import NotificationPreference

    result = await session.execute(select(Member).where(Member.phone == phone_number))
    members = list(result.scalars().all())

    if not members:
        logger.warning(
            "RESUME from unknown phone phone_hash=%s — no member found",
            hash_for_log(phone_number),
        )
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
        "Resumed immediate delivery for phone_hash=%s (%d member(s))",
        hash_for_log(phone_number),
        len(members),
    )
