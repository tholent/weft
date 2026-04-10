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

"""Tests for SMS command parsing and inbound webhook handler."""

import pytest
from sqlmodel import select

from app.models.enums import DeliveryMode, MemberRole, NotificationChannel, NotificationTrigger
from app.models.member import Member
from app.models.notification import NotificationPreference
from app.services.notifications.sms_commands import SmsCommand, is_sms_command, parse_sms_command

# ---------------------------------------------------------------------------
# parse_sms_command unit tests
# ---------------------------------------------------------------------------


class TestParseSmsCommand:
    def test_stop_command(self):
        assert parse_sms_command("STOP") == SmsCommand.stop

    def test_stop_lowercase(self):
        assert parse_sms_command("stop") == SmsCommand.stop

    def test_stop_mixed_case(self):
        assert parse_sms_command("Stop") == SmsCommand.stop

    def test_stop_with_whitespace(self):
        assert parse_sms_command("  STOP  ") == SmsCommand.stop

    def test_mute_command(self):
        assert parse_sms_command("MUTE") == SmsCommand.mute

    def test_mute_lowercase(self):
        assert parse_sms_command("mute") == SmsCommand.mute

    def test_resume_command(self):
        assert parse_sms_command("RESUME") == SmsCommand.resume

    def test_resume_lowercase(self):
        assert parse_sms_command("resume") == SmsCommand.resume

    def test_list_command(self):
        assert parse_sms_command("LIST") == SmsCommand.list

    def test_list_lowercase(self):
        assert parse_sms_command("list") == SmsCommand.list

    def test_non_command_returns_none(self):
        assert parse_sms_command("Hello, how are you?") is None

    def test_partial_command_returns_none(self):
        assert parse_sms_command("STOP please") is None

    def test_empty_string_returns_none(self):
        assert parse_sms_command("") is None

    def test_whitespace_only_returns_none(self):
        assert parse_sms_command("   ") is None

    def test_number_returns_none(self):
        assert parse_sms_command("12345") is None

    def test_reply_text_returns_none(self):
        assert parse_sms_command("I want to reply to the update") is None

    def test_stop_with_extra_text_returns_none(self):
        assert parse_sms_command("STOP all messages") is None


class TestIsSmsCommand:
    def test_stop_is_command(self):
        assert is_sms_command("STOP") is True

    def test_mute_is_command(self):
        assert is_sms_command("MUTE") is True

    def test_resume_is_command(self):
        assert is_sms_command("RESUME") is True

    def test_list_is_command(self):
        assert is_sms_command("LIST") is True

    def test_regular_text_is_not_command(self):
        assert is_sms_command("Hello there") is False

    def test_empty_is_not_command(self):
        assert is_sms_command("") is False


# ---------------------------------------------------------------------------
# Inbound webhook HTTP tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_sms_inbound_stop_mutes_member(client, session, topic_with_creator):
    """STOP command from a known phone number mutes all triggers for that member."""
    topic, creator, _ = topic_with_creator

    sms_member = Member(
        topic_id=topic.id,
        role=MemberRole.recipient,
        phone="+15550001234",
        notification_channel=NotificationChannel.sms,
    )
    session.add(sms_member)
    await session.commit()

    resp = await client.post(
        "/webhooks/sms/inbound",
        data={"From": "+15550001234", "Body": "STOP", "To": "+15559999999"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"

    # Verify preferences were created / updated to muted
    prefs_result = await session.execute(
        select(NotificationPreference).where(
            NotificationPreference.member_id == sms_member.id
        )
    )
    prefs = list(prefs_result.scalars().all())
    assert len(prefs) == len(list(NotificationTrigger))
    for pref in prefs:
        assert pref.delivery_mode == DeliveryMode.muted


@pytest.mark.anyio
async def test_sms_inbound_mute_alias_works(client, session, topic_with_creator):
    """MUTE command behaves identically to STOP."""
    topic, creator, _ = topic_with_creator

    sms_member = Member(
        topic_id=topic.id,
        role=MemberRole.recipient,
        phone="+15550005678",
        notification_channel=NotificationChannel.sms,
    )
    session.add(sms_member)
    await session.commit()

    resp = await client.post(
        "/webhooks/sms/inbound",
        data={"From": "+15550005678", "Body": "MUTE", "To": "+15559999999"},
    )
    assert resp.status_code == 200

    prefs_result = await session.execute(
        select(NotificationPreference).where(
            NotificationPreference.member_id == sms_member.id
        )
    )
    prefs = list(prefs_result.scalars().all())
    for pref in prefs:
        assert pref.delivery_mode == DeliveryMode.muted


@pytest.mark.anyio
async def test_sms_inbound_resume_re_enables_delivery(client, session, topic_with_creator):
    """RESUME command sets all triggers back to immediate delivery."""
    topic, creator, _ = topic_with_creator

    sms_member = Member(
        topic_id=topic.id,
        role=MemberRole.recipient,
        phone="+15550009999",
        notification_channel=NotificationChannel.sms,
    )
    session.add(sms_member)
    await session.flush()

    # First mute the member
    for trigger in NotificationTrigger:
        pref = NotificationPreference(
            member_id=sms_member.id,
            channel=NotificationChannel.sms,
            trigger=trigger,
            delivery_mode=DeliveryMode.muted,
        )
        session.add(pref)
    await session.commit()

    resp = await client.post(
        "/webhooks/sms/inbound",
        data={"From": "+15550009999", "Body": "RESUME", "To": "+15559999999"},
    )
    assert resp.status_code == 200

    prefs_result = await session.execute(
        select(NotificationPreference)
        .where(NotificationPreference.member_id == sms_member.id)
        .execution_options(populate_existing=True)
    )
    prefs = list(prefs_result.scalars().all())
    for pref in prefs:
        assert pref.delivery_mode == DeliveryMode.immediate


@pytest.mark.anyio
async def test_sms_inbound_list_command_acknowledged(client):
    """LIST command returns accepted status (implementation reserved)."""
    resp = await client.post(
        "/webhooks/sms/inbound",
        data={"From": "+15550001111", "Body": "LIST", "To": "+15559999999"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"


@pytest.mark.anyio
async def test_sms_inbound_non_command_reply_accepted(client):
    """Non-command SMS is logged and accepted without error."""
    resp = await client.post(
        "/webhooks/sms/inbound",
        data={
            "From": "+15550002222",
            "Body": "Thanks for the update! Hope everything goes well.",
            "To": "+15559999999",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"


@pytest.mark.anyio
async def test_sms_inbound_stop_unknown_phone_accepted(client):
    """STOP from an unknown phone number returns 200 without crashing."""
    resp = await client.post(
        "/webhooks/sms/inbound",
        data={"From": "+19990000000", "Body": "STOP", "To": "+15559999999"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"


@pytest.mark.anyio
async def test_sms_inbound_resume_unknown_phone_accepted(client):
    """RESUME from an unknown phone number returns 200 without crashing."""
    resp = await client.post(
        "/webhooks/sms/inbound",
        data={"From": "+19990000001", "Body": "RESUME", "To": "+15559999999"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"


@pytest.mark.anyio
async def test_sms_inbound_updates_existing_preferences(client, session, topic_with_creator):
    """STOP on a member who already has preferences updates them rather than duplicating."""
    topic, creator, _ = topic_with_creator

    sms_member = Member(
        topic_id=topic.id,
        role=MemberRole.recipient,
        phone="+15550007777",
        notification_channel=NotificationChannel.sms,
    )
    session.add(sms_member)
    await session.flush()

    # Pre-create preferences with immediate delivery
    for trigger in NotificationTrigger:
        pref = NotificationPreference(
            member_id=sms_member.id,
            channel=NotificationChannel.sms,
            trigger=trigger,
            delivery_mode=DeliveryMode.immediate,
        )
        session.add(pref)
    await session.commit()

    resp = await client.post(
        "/webhooks/sms/inbound",
        data={"From": "+15550007777", "Body": "STOP", "To": "+15559999999"},
    )
    assert resp.status_code == 200

    prefs_result = await session.execute(
        select(NotificationPreference)
        .where(NotificationPreference.member_id == sms_member.id)
        .execution_options(populate_existing=True)
    )
    prefs = list(prefs_result.scalars().all())
    # Should still have the same count (no duplicates)
    assert len(prefs) == len(list(NotificationTrigger))
    for pref in prefs:
        assert pref.delivery_mode == DeliveryMode.muted
