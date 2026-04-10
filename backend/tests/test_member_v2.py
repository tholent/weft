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

"""Tests for member invitation validation, channel constraints, purge, and notification prefs."""

import pytest
from sqlmodel import select

from app.models.circle import Circle
from app.models.enums import NotificationChannel
from app.models.member import Member
from app.models.notification import NotificationPreference
from app.services.member import invite_member
from app.services.purge import purge_emails

# ---------------------------------------------------------------------------
# Invitation validation
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_invite_email_only_channel_email_succeeds(session, topic_with_creator):
    """Inviting with email only and channel=email succeeds."""
    topic, creator, _ = topic_with_creator

    circle = Circle(topic_id=topic.id, name="Test Circle")
    session.add(circle)
    await session.flush()

    member, raw_token = await invite_member(
        session,
        topic_id=topic.id,
        circle_id=circle.id,
        email="invited@example.com",
        phone=None,
        notification_channel=NotificationChannel.email,
    )
    await session.commit()

    assert member.id is not None
    assert member.email == "invited@example.com"
    assert member.phone is None
    assert member.notification_channel == NotificationChannel.email
    assert raw_token


@pytest.mark.anyio
async def test_invite_phone_only_channel_sms_succeeds(session, topic_with_creator):
    """Inviting with phone only and channel=sms succeeds."""
    topic, creator, _ = topic_with_creator

    circle = Circle(topic_id=topic.id, name="SMS Circle")
    session.add(circle)
    await session.flush()

    member, raw_token = await invite_member(
        session,
        topic_id=topic.id,
        circle_id=circle.id,
        email=None,
        phone="+15550001234",
        notification_channel=NotificationChannel.sms,
    )
    await session.commit()

    assert member.id is not None
    assert member.phone == "+15550001234"
    assert member.email is None
    assert member.notification_channel == NotificationChannel.sms
    assert raw_token


@pytest.mark.anyio
async def test_invite_channel_sms_without_phone_raises_error(session, topic_with_creator):
    """Inviting with channel=sms but no phone number raises ValueError."""
    topic, creator, _ = topic_with_creator

    circle = Circle(topic_id=topic.id, name="Bad Circle")
    session.add(circle)
    await session.flush()

    with pytest.raises(ValueError, match="Phone is required when notification_channel is sms"):
        await invite_member(
            session,
            topic_id=topic.id,
            circle_id=circle.id,
            email="has-email@example.com",
            phone=None,
            notification_channel=NotificationChannel.sms,
        )


@pytest.mark.anyio
async def test_invite_channel_email_without_email_raises_error(session, topic_with_creator):
    """Inviting with channel=email but no email address raises ValueError."""
    topic, creator, _ = topic_with_creator

    circle = Circle(topic_id=topic.id, name="Bad Circle 2")
    session.add(circle)
    await session.flush()

    with pytest.raises(ValueError, match="Email is required when notification_channel is email"):
        await invite_member(
            session,
            topic_id=topic.id,
            circle_id=circle.id,
            email=None,
            phone="+15550001234",
            notification_channel=NotificationChannel.email,
        )


@pytest.mark.anyio
async def test_invite_no_contact_at_all_raises_error(session, topic_with_creator):
    """Inviting with neither email nor phone raises ValueError."""
    topic, creator, _ = topic_with_creator

    circle = Circle(topic_id=topic.id, name="Empty Circle")
    session.add(circle)
    await session.flush()

    with pytest.raises(ValueError, match="At least one of email or phone must be provided"):
        await invite_member(
            session,
            topic_id=topic.id,
            circle_id=circle.id,
            email=None,
            phone=None,
            notification_channel=NotificationChannel.email,
        )


# ---------------------------------------------------------------------------
# Purge contact info
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_purge_clears_both_email_and_phone(session, topic_with_creator):
    """purge_emails sets both email and phone to None for all members."""
    topic, creator, _ = topic_with_creator

    circle = Circle(topic_id=topic.id, name="Purge Circle")
    session.add(circle)
    await session.flush()

    member, _ = await invite_member(
        session,
        topic_id=topic.id,
        circle_id=circle.id,
        email="contact@example.com",
        phone="+15550009999",
        notification_channel=NotificationChannel.email,
    )
    await session.flush()

    await purge_emails(session, topic.id)
    await session.flush()

    result = await session.execute(select(Member).where(Member.id == member.id))
    m = result.scalar_one()
    assert m.email is None
    assert m.phone is None
    assert m.email_purged_at is not None
    assert m.phone_purged_at is not None


# ---------------------------------------------------------------------------
# NotificationPreference created on invite
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_invite_creates_notification_preferences(session, topic_with_creator):
    """invite_member creates default NotificationPreference rows for the new member."""
    topic, creator, _ = topic_with_creator

    circle = Circle(topic_id=topic.id, name="Pref Circle")
    session.add(circle)
    await session.flush()

    member, _ = await invite_member(
        session,
        topic_id=topic.id,
        circle_id=circle.id,
        email="prefs@example.com",
        notification_channel=NotificationChannel.email,
    )
    await session.commit()

    result = await session.execute(
        select(NotificationPreference).where(NotificationPreference.member_id == member.id)
    )
    prefs = list(result.scalars().all())

    # There should be a preference for each trigger
    from app.models.enums import NotificationTrigger

    trigger_set = {p.trigger for p in prefs}
    assert len(prefs) > 0
    for trigger in NotificationTrigger:
        assert trigger in trigger_set, f"Missing preference for trigger {trigger}"
