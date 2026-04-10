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

"""Tests for the notification preferences HTTP endpoints."""

import pytest

from app.models.enums import (
    DeliveryMode,
    MemberRole,
    NotificationChannel,
    NotificationTrigger,
)
from app.models.member import Member
from app.models.notification import NotificationPreference
from app.services.auth import generate_token

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_member_with_prefs(session, topic_id, email, role=MemberRole.recipient):
    """Create a member and seed one notification preference for them."""
    member = Member(topic_id=topic_id, role=role, email=email)
    session.add(member)
    await session.flush()

    pref = NotificationPreference(
        member_id=member.id,
        channel=NotificationChannel.email,
        trigger=NotificationTrigger.new_update,
        delivery_mode=DeliveryMode.immediate,
    )
    session.add(pref)
    await session.flush()

    raw_token = await generate_token(session, member.id)
    return member, pref, raw_token


# ---------------------------------------------------------------------------
# GET preferences
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_preferences_returns_current_settings(client, session, topic_with_creator):
    """GET /notifications returns all preferences for the requesting member."""
    topic, creator, creator_token = topic_with_creator

    member, pref, member_token = await _create_member_with_prefs(
        session, topic.id, "pref-test@example.com"
    )
    await session.commit()

    resp = await client.get(
        f"/topics/{topic.id}/members/{member.id}/notifications",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    # Verify the seeded preference is present
    pref_data = next((p for p in data if p["trigger"] == NotificationTrigger.new_update), None)
    assert pref_data is not None
    assert pref_data["channel"] == NotificationChannel.email
    assert pref_data["delivery_mode"] == DeliveryMode.immediate


@pytest.mark.anyio
async def test_get_preferences_owner_can_view_any_member(client, session, topic_with_creator):
    """Owner can retrieve preferences for any member in their topic."""
    topic, creator, creator_token = topic_with_creator

    member, pref, _ = await _create_member_with_prefs(session, topic.id, "member@example.com")
    await session.commit()

    resp = await client.get(
        f"/topics/{topic.id}/members/{member.id}/notifications",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_get_preferences_recipient_cannot_view_other_member(
    client, session, topic_with_creator
):
    """A recipient cannot view another member's preferences."""
    topic, creator, _ = topic_with_creator

    member_a, _, token_a = await _create_member_with_prefs(
        session, topic.id, "member-a@example.com"
    )
    member_b, _, token_b = await _create_member_with_prefs(
        session, topic.id, "member-b@example.com"
    )
    await session.commit()

    resp = await client.get(
        f"/topics/{topic.id}/members/{member_b.id}/notifications",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PUT / update preference
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_put_preference_updates_only_provided_fields(client, session, topic_with_creator):
    """PUT /notifications creates or updates a single preference entry."""
    topic, creator, _ = topic_with_creator

    member, pref, member_token = await _create_member_with_prefs(
        session, topic.id, "update-test@example.com"
    )
    await session.commit()

    resp = await client.put(
        f"/topics/{topic.id}/members/{member.id}/notifications",
        headers={"Authorization": f"Bearer {member_token}"},
        json={
            "channel": NotificationChannel.email,
            "trigger": NotificationTrigger.new_update,
            "delivery_mode": DeliveryMode.digest,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["delivery_mode"] == DeliveryMode.digest
    assert data["trigger"] == NotificationTrigger.new_update
    assert data["channel"] == NotificationChannel.email


@pytest.mark.anyio
async def test_put_preference_member_cannot_modify_other_member(
    client, session, topic_with_creator
):
    """A member cannot modify another member's notification preferences."""
    topic, creator, _ = topic_with_creator

    member_a, _, token_a = await _create_member_with_prefs(session, topic.id, "a@example.com")
    member_b, _, token_b = await _create_member_with_prefs(session, topic.id, "b@example.com")
    await session.commit()

    resp = await client.put(
        f"/topics/{topic.id}/members/{member_b.id}/notifications",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "channel": NotificationChannel.email,
            "trigger": NotificationTrigger.new_update,
            "delivery_mode": DeliveryMode.muted,
        },
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_put_preference_invalid_delivery_mode_rejected(client, session, topic_with_creator):
    """PUT with an invalid delivery_mode value returns 422."""
    topic, creator, _ = topic_with_creator

    member, _, member_token = await _create_member_with_prefs(
        session, topic.id, "invalid@example.com"
    )
    await session.commit()

    resp = await client.put(
        f"/topics/{topic.id}/members/{member.id}/notifications",
        headers={"Authorization": f"Bearer {member_token}"},
        json={
            "channel": NotificationChannel.email,
            "trigger": NotificationTrigger.new_update,
            "delivery_mode": "every_other_tuesday",
        },
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_put_preference_invalid_channel_rejected(client, session, topic_with_creator):
    """PUT with an invalid channel value returns 422."""
    topic, creator, _ = topic_with_creator

    member, _, member_token = await _create_member_with_prefs(
        session, topic.id, "badchannel@example.com"
    )
    await session.commit()

    resp = await client.put(
        f"/topics/{topic.id}/members/{member.id}/notifications",
        headers={"Authorization": f"Bearer {member_token}"},
        json={
            "channel": "carrier_pigeon",
            "trigger": NotificationTrigger.new_update,
            "delivery_mode": DeliveryMode.immediate,
        },
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_put_preference_muted_delivery_mode(client, session, topic_with_creator):
    """A member can set delivery_mode to muted to silence notifications."""
    topic, creator, _ = topic_with_creator

    member, _, member_token = await _create_member_with_prefs(
        session, topic.id, "muted@example.com"
    )
    await session.commit()

    resp = await client.put(
        f"/topics/{topic.id}/members/{member.id}/notifications",
        headers={"Authorization": f"Bearer {member_token}"},
        json={
            "channel": NotificationChannel.email,
            "trigger": NotificationTrigger.new_reply,
            "delivery_mode": DeliveryMode.muted,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["delivery_mode"] == DeliveryMode.muted
