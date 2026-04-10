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

"""Tests for the topic export endpoint and service."""

import pytest

from app.models.circle import Circle
from app.models.enums import MemberRole
from app.models.member import Member
from app.models.update import Update
from app.services.auth import generate_token

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_member(session, topic_id, email, role):
    member = Member(topic_id=topic_id, role=role, email=email)
    session.add(member)
    await session.flush()
    raw_token = await generate_token(session, member.id)
    return member, raw_token


# ---------------------------------------------------------------------------
# Permission tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_export_owner_can_export(client, session, topic_with_creator):
    """Topic owner can trigger an export."""
    topic, creator, creator_token = topic_with_creator

    resp = await client.get(
        f"/topics/{topic.id}/export",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "topic" in data
    assert "circles" in data
    assert "updates" in data


@pytest.mark.anyio
async def test_export_admin_cannot_export(client, session, topic_with_creator):
    """Admin cannot export — only owner is allowed."""
    topic, creator, _ = topic_with_creator

    admin, admin_token = await _make_member(
        session, topic.id, "admin@example.com", MemberRole.admin
    )
    await session.commit()

    resp = await client.get(
        f"/topics/{topic.id}/export",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_export_moderator_cannot_export(client, session, topic_with_creator):
    """Moderator cannot export — returns 403."""
    topic, creator, _ = topic_with_creator

    mod, mod_token = await _make_member(session, topic.id, "mod@example.com", MemberRole.moderator)
    await session.commit()

    resp = await client.get(
        f"/topics/{topic.id}/export",
        headers={"Authorization": f"Bearer {mod_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_export_recipient_cannot_export(client, session, topic_with_creator):
    """Recipient cannot export — returns 403."""
    topic, creator, _ = topic_with_creator

    recipient, rec_token = await _make_member(
        session, topic.id, "recipient@example.com", MemberRole.recipient
    )
    await session.commit()

    resp = await client.get(
        f"/topics/{topic.id}/export",
        headers={"Authorization": f"Bearer {rec_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_export_unauthenticated_rejected(client, session, topic_with_creator):
    """Unauthenticated request returns 401."""
    topic, creator, _ = topic_with_creator

    resp = await client.get(f"/topics/{topic.id}/export")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Data structure and PII exclusion tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_export_includes_all_data(client, session, topic_with_creator):
    """Export response includes topic, circles, updates, relays, and exported_at."""
    topic, creator, creator_token = topic_with_creator

    # Add a circle
    circle = Circle(topic_id=topic.id, name="Export Circle")
    session.add(circle)
    await session.flush()

    # Add an update
    update = Update(topic_id=topic.id, author_member_id=creator.id, body="Exported update body")
    session.add(update)
    await session.commit()

    resp = await client.get(
        f"/topics/{topic.id}/export",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert "topic" in data
    assert "circles" in data
    assert "updates" in data
    assert "relays" in data
    assert "exported_at" in data

    # Check topic metadata
    assert data["topic"]["title"] == topic.default_title
    assert data["topic"]["status"] == "active"

    # Check circle is present
    circle_names = [c["name"] for c in data["circles"]]
    assert "Export Circle" in circle_names

    # Check update is present
    update_bodies = [u["body"] for u in data["updates"]]
    assert "Exported update body" in update_bodies


@pytest.mark.anyio
async def test_export_excludes_pii(client, session, topic_with_creator):
    """Export does not include email addresses or phone numbers."""
    topic, creator, creator_token = topic_with_creator

    member, _ = await _make_member(session, topic.id, "pii-test@example.com", MemberRole.recipient)
    await session.commit()

    resp = await client.get(
        f"/topics/{topic.id}/export",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    raw = resp.text

    # Email and phone should not appear in the export output
    assert "pii-test@example.com" not in raw
    assert "creator@test.com" not in raw


@pytest.mark.anyio
async def test_export_empty_topic(client, session, topic_with_creator):
    """Export works for a topic with no circles, updates, or relays."""
    topic, creator, creator_token = topic_with_creator

    resp = await client.get(
        f"/topics/{topic.id}/export",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["circles"] == []
    assert data["updates"] == []
    assert data["relays"] == []


@pytest.mark.anyio
async def test_export_response_has_content_disposition_header(client, session, topic_with_creator):
    """Export response includes Content-Disposition header for file download."""
    topic, creator, creator_token = topic_with_creator

    resp = await client.get(
        f"/topics/{topic.id}/export",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    assert "content-disposition" in resp.headers
    assert "attachment" in resp.headers["content-disposition"]
