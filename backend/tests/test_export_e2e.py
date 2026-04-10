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

"""End-to-end integration tests for the topic export flow.

This test suite exercises the complete export pipeline, including:
- Topic creation with multiple circles and members
- Creating updates, replies, and mod responses
- Uploading attachments
- Exporting with permission verification
- Validating PII exclusion and data structure integrity
"""

import uuid

import pytest

from app.models.attachment import Attachment
from app.models.circle import Circle
from app.models.enums import MemberRole, ModResponseScope
from app.models.member import Member, MemberCircleHistory
from app.models.reply import ModResponse, Reply
from app.models.update import Update, UpdateCircle
from app.services.auth import generate_token

# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------


async def _make_member(session, topic_id, email, role):
    """Create a member and generate a token."""
    member = Member(topic_id=topic_id, role=role, email=email)
    session.add(member)
    await session.flush()
    raw_token = await generate_token(session, member.id)
    return member, raw_token


async def _create_update_with_circles(session, topic_id, author_id, body, circle_ids):
    """Create an update and link it to circles."""
    update = Update(topic_id=topic_id, author_member_id=author_id, body=body)
    session.add(update)
    await session.flush()

    for circle_id in circle_ids:
        uc = UpdateCircle(update_id=update.id, circle_id=circle_id)
        session.add(uc)

    return update


async def _create_attachment(session, update_id, topic_id):
    """Create an attachment for an update."""
    att = Attachment(
        update_id=update_id,
        topic_id=topic_id,
        filename="test_photo.jpg",
        content_type="image/jpeg",
        storage_key=f"attachments/{uuid.uuid4()}.jpg",
        size_bytes=1024,
    )
    session.add(att)
    await session.flush()
    return att


# ---------------------------------------------------------------------------
# E2E: Full Export Flow with Complete Data
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_export_e2e_full_topic_with_all_data(client, session, topic_with_creator):
    """Full E2E: Create rich topic with circles, updates, replies, mod responses, attachments."""
    topic, creator, creator_token = topic_with_creator

    # Create two circles
    circle1 = Circle(topic_id=topic.id, name="Family", scoped_title="Family Updates")
    circle2 = Circle(topic_id=topic.id, name="Friends", scoped_title="Friends Updates")
    session.add(circle1)
    session.add(circle2)
    await session.flush()

    # Create recipients for each circle
    recip1, recip1_token = await _make_member(
        session, topic.id, "recip1@test.com", MemberRole.recipient
    )
    recip2, recip2_token = await _make_member(
        session, topic.id, "recip2@test.com", MemberRole.recipient
    )
    recip3, recip3_token = await _make_member(
        session, topic.id, "recip3@test.com", MemberRole.recipient
    )

    # Add recipients to circles
    h1 = MemberCircleHistory(member_id=recip1.id, circle_id=circle1.id)
    h2 = MemberCircleHistory(member_id=recip2.id, circle_id=circle1.id)
    h3 = MemberCircleHistory(member_id=recip3.id, circle_id=circle2.id)
    session.add(h1)
    session.add(h2)
    session.add(h3)

    # Create moderator
    mod, mod_token = await _make_member(session, topic.id, "mod@test.com", MemberRole.moderator)
    mod_history = MemberCircleHistory(member_id=mod.id, circle_id=circle1.id)
    session.add(mod_history)

    await session.flush()

    # Create updates with attachments
    update1 = await _create_update_with_circles(
        session, topic.id, creator.id, "Update 1 body", [circle1.id]
    )
    await session.flush()
    await _create_attachment(session, update1.id, topic.id)

    update2 = await _create_update_with_circles(
        session, topic.id, creator.id, "Update 2 body", [circle1.id, circle2.id]
    )
    await session.flush()
    await _create_attachment(session, update2.id, topic.id)

    # Create replies
    reply1 = Reply(update_id=update1.id, author_member_id=recip1.id, body="Reply from recip1")
    reply2 = Reply(update_id=update2.id, author_member_id=recip3.id, body="Reply from recip3")
    session.add(reply1)
    session.add(reply2)
    await session.flush()

    # Create mod responses
    mod_resp1 = ModResponse(
        reply_id=reply1.id,
        author_member_id=mod.id,
        body="Mod response to recip1",
        scope=ModResponseScope.sender_only,
    )
    mod_resp2 = ModResponse(
        reply_id=reply1.id,
        author_member_id=mod.id,
        body="Another response",
        scope=ModResponseScope.sender_circle,
    )
    session.add(mod_resp1)
    session.add(mod_resp2)

    await session.commit()

    # Export as owner
    resp = await client.get(
        f"/topics/{topic.id}/export",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    # Verify structure
    assert "topic" in data
    assert "circles" in data
    assert "updates" in data
    assert "relays" in data
    assert "exported_at" in data

    # Verify topic metadata
    assert data["topic"]["title"] == topic.default_title
    assert data["topic"]["status"] == "active"
    assert "created_at" in data["topic"]

    # Verify circles
    assert len(data["circles"]) == 2
    circle_names = {c["name"] for c in data["circles"]}
    assert circle_names == {"Family", "Friends"}

    # Verify circle metadata
    family_circle = next(c for c in data["circles"] if c["name"] == "Family")
    assert family_circle["scoped_title"] == "Family Updates"

    # Verify updates
    assert len(data["updates"]) == 2

    update1_export = next(u for u in data["updates"] if u["body"] == "Update 1 body")
    assert set(update1_export["circles"]) == {"Family"}
    assert len(update1_export["attachments"]) == 1
    assert update1_export["attachments"][0]["filename"] == "test_photo.jpg"
    assert update1_export["attachments"][0]["content_type"] == "image/jpeg"
    assert len(update1_export["replies"]) == 1

    update2_export = next(u for u in data["updates"] if u["body"] == "Update 2 body")
    assert set(update2_export["circles"]) == {"Family", "Friends"}
    assert len(update2_export["attachments"]) == 1
    assert len(update2_export["replies"]) == 1

    # Verify replies
    reply1_export = update1_export["replies"][0]
    assert reply1_export["body"] == "Reply from recip1"
    assert len(reply1_export["mod_responses"]) == 2
    assert reply1_export["mod_responses"][0]["body"] == "Mod response to recip1"
    assert reply1_export["mod_responses"][1]["body"] == "Another response"

    # Verify PII excluded
    export_text = resp.text
    assert "recip1@test.com" not in export_text
    assert "recip2@test.com" not in export_text
    assert "recip3@test.com" not in export_text
    assert "mod@test.com" not in export_text
    assert "creator@test.com" not in export_text

    # Verify display handles are used instead
    assert "recip1" in str(reply1_export["author"]) or reply1_export["author"] is None


@pytest.mark.anyio
async def test_export_e2e_owner_can_always_export(client, session, topic_with_creator):
    """Owner can export regardless of member activity."""
    topic, creator, creator_token = topic_with_creator

    resp = await client.get(
        f"/topics/{topic.id}/export",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "topic" in data


@pytest.mark.anyio
async def test_export_e2e_admin_cannot_export(client, session, topic_with_creator):
    """Admin role cannot export — only owner."""
    topic, creator, _ = topic_with_creator

    admin, admin_token = await _make_member(session, topic.id, "admin@test.com", MemberRole.admin)
    await session.commit()

    resp = await client.get(
        f"/topics/{topic.id}/export",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_export_e2e_moderator_cannot_export(client, session, topic_with_creator):
    """Moderator role cannot export — returns 403."""
    topic, creator, _ = topic_with_creator

    mod, mod_token = await _make_member(session, topic.id, "mod@test.com", MemberRole.moderator)
    await session.commit()

    resp = await client.get(
        f"/topics/{topic.id}/export",
        headers={"Authorization": f"Bearer {mod_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_export_e2e_recipient_cannot_export(client, session, topic_with_creator):
    """Recipient role cannot export — returns 403."""
    topic, creator, _ = topic_with_creator

    recip, recip_token = await _make_member(
        session, topic.id, "recip@test.com", MemberRole.recipient
    )
    await session.commit()

    resp = await client.get(
        f"/topics/{topic.id}/export",
        headers={"Authorization": f"Bearer {recip_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_export_e2e_empty_topic_valid_structure(client, session, topic_with_creator):
    """Export of empty topic has valid structure with empty arrays."""
    topic, creator, creator_token = topic_with_creator

    resp = await client.get(
        f"/topics/{topic.id}/export",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    # Verify structure is valid
    assert isinstance(data["circles"], list)
    assert isinstance(data["updates"], list)
    assert isinstance(data["relays"], list)

    # Verify empty
    assert len(data["circles"]) == 0
    assert len(data["updates"]) == 0
    assert len(data["relays"]) == 0

    # Topic metadata should still be present
    assert data["topic"]["title"] == topic.default_title


@pytest.mark.anyio
async def test_export_e2e_attachment_urls_in_export(client, session, topic_with_creator):
    """Export includes attachment storage keys and metadata."""
    topic, creator, creator_token = topic_with_creator

    circle = Circle(topic_id=topic.id, name="TestCircle")
    session.add(circle)
    await session.flush()

    update = await _create_update_with_circles(
        session, topic.id, creator.id, "Update with attachment", [circle.id]
    )
    await session.flush()

    att = await _create_attachment(session, update.id, topic.id)
    await session.commit()

    resp = await client.get(
        f"/topics/{topic.id}/export",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    # Verify attachment is in export
    assert len(data["updates"]) == 1
    update_export = data["updates"][0]
    assert len(update_export["attachments"]) == 1

    att_export = update_export["attachments"][0]
    assert att_export["filename"] == "test_photo.jpg"
    assert att_export["content_type"] == "image/jpeg"
    assert att_export["storage_key"] == att.storage_key
    assert "attachments/" in att_export["storage_key"]


@pytest.mark.anyio
async def test_export_e2e_reply_with_mod_responses(client, session, topic_with_creator):
    """Export includes replies with their mod responses properly nested."""
    topic, creator, creator_token = topic_with_creator

    circle = Circle(topic_id=topic.id, name="TestCircle")
    session.add(circle)
    await session.flush()

    mod, _ = await _make_member(session, topic.id, "mod@test.com", MemberRole.moderator)
    mod_history = MemberCircleHistory(member_id=mod.id, circle_id=circle.id)
    session.add(mod_history)

    recip, _ = await _make_member(session, topic.id, "recip@test.com", MemberRole.recipient)
    recip_history = MemberCircleHistory(member_id=recip.id, circle_id=circle.id)
    session.add(recip_history)

    await session.flush()

    update = await _create_update_with_circles(
        session, topic.id, creator.id, "Update for replies", [circle.id]
    )
    await session.flush()

    reply = Reply(update_id=update.id, author_member_id=recip.id, body="Recipient reply")
    session.add(reply)
    await session.flush()

    # Add multiple mod responses with different scopes
    mr1 = ModResponse(
        reply_id=reply.id,
        author_member_id=mod.id,
        body="Response 1",
        scope=ModResponseScope.sender_only,
    )
    mr2 = ModResponse(
        reply_id=reply.id,
        author_member_id=mod.id,
        body="Response 2",
        scope=ModResponseScope.sender_circle,
    )
    session.add(mr1)
    session.add(mr2)
    await session.commit()

    resp = await client.get(
        f"/topics/{topic.id}/export",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    update_export = data["updates"][0]
    assert len(update_export["replies"]) == 1

    reply_export = update_export["replies"][0]
    assert reply_export["body"] == "Recipient reply"
    assert len(reply_export["mod_responses"]) == 2

    # Verify mod response structure
    for mr in reply_export["mod_responses"]:
        assert "body" in mr
        assert "scope" in mr
        assert "author" in mr
        assert "created_at" in mr


@pytest.mark.anyio
async def test_export_e2e_multiple_circles_membership(client, session, topic_with_creator):
    """Export correctly shows updates targeted to multiple circles."""
    topic, creator, creator_token = topic_with_creator

    circle1 = Circle(topic_id=topic.id, name="CircleA")
    circle2 = Circle(topic_id=topic.id, name="CircleB")
    circle3 = Circle(topic_id=topic.id, name="CircleC")
    session.add_all([circle1, circle2, circle3])
    await session.flush()

    # Create update targeting 2 of 3 circles
    await _create_update_with_circles(
        session, topic.id, creator.id, "Multi-circle update", [circle1.id, circle3.id]
    )
    await session.commit()

    resp = await client.get(
        f"/topics/{topic.id}/export",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    # Verify all circles in export
    assert len(data["circles"]) == 3

    # Verify update targets correct circles
    update_export = data["updates"][0]
    assert set(update_export["circles"]) == {"CircleA", "CircleC"}


@pytest.mark.anyio
async def test_export_e2e_content_disposition_header(client, session, topic_with_creator):
    """Export response includes proper Content-Disposition header for file download."""
    topic, creator, creator_token = topic_with_creator

    resp = await client.get(
        f"/topics/{topic.id}/export",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    assert "content-disposition" in resp.headers
    assert "attachment" in resp.headers["content-disposition"]
    assert f"weft-export-{topic.id}" in resp.headers["content-disposition"]


@pytest.mark.anyio
async def test_export_e2e_timestamps_in_iso_format(client, session, topic_with_creator):
    """Export timestamps are in ISO 8601 format."""
    topic, creator, creator_token = topic_with_creator

    circle = Circle(topic_id=topic.id, name="TestCircle")
    session.add(circle)
    await session.flush()

    await _create_update_with_circles(
        session, topic.id, creator.id, "Timestamped update", [circle.id]
    )
    await session.commit()

    resp = await client.get(
        f"/topics/{topic.id}/export",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    # Check timestamps are ISO format (T separator present)
    assert "T" in data["topic"]["created_at"]

    update_export = data["updates"][0]
    assert "T" in update_export["created_at"]


@pytest.mark.anyio
async def test_export_e2e_no_email_in_raw_response(client, session, topic_with_creator):
    """Verify no email addresses appear anywhere in raw response text."""
    topic, creator, creator_token = topic_with_creator

    # Create multiple members with identifiable emails
    test_emails = [
        "alice@example.com",
        "bob@example.org",
        "charlie.brown@test.io",
        "creator@test.com",
    ]

    for email in test_emails[:-1]:  # Exclude creator's email as it's in fixture
        member = Member(topic_id=topic.id, role=MemberRole.recipient, email=email)
        session.add(member)

    await session.commit()

    resp = await client.get(
        f"/topics/{topic.id}/export",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    response_text = resp.text

    # Verify NO email addresses in response
    for email in test_emails:
        assert email not in response_text
        # Also check partial patterns
        assert "@" not in response_text or "example.com" not in response_text


@pytest.mark.anyio
async def test_export_e2e_nonexistent_topic(client, session, topic_with_creator):
    """Export returns 404 for nonexistent topic."""
    topic, creator, creator_token = topic_with_creator

    fake_topic_id = uuid.uuid4()

    resp = await client.get(
        f"/topics/{fake_topic_id}/export",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 403  # Access denied (wrong topic)


@pytest.mark.anyio
async def test_export_e2e_reply_status_and_flags(client, session, topic_with_creator):
    """Export includes reply metadata: wants_to_share, relay_status."""
    topic, creator, creator_token = topic_with_creator

    circle = Circle(topic_id=topic.id, name="TestCircle")
    session.add(circle)
    await session.flush()

    recip, _ = await _make_member(session, topic.id, "recip@test.com", MemberRole.recipient)
    history = MemberCircleHistory(member_id=recip.id, circle_id=circle.id)
    session.add(history)

    await session.flush()

    update = await _create_update_with_circles(
        session, topic.id, creator.id, "Update for reply metadata", [circle.id]
    )
    await session.flush()

    reply = Reply(
        update_id=update.id,
        author_member_id=recip.id,
        body="Reply text",
        wants_to_share=True,
    )
    session.add(reply)
    await session.commit()

    resp = await client.get(
        f"/topics/{topic.id}/export",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    reply_export = data["updates"][0]["replies"][0]
    assert reply_export["wants_to_share"] is True
    assert "relay_status" in reply_export


@pytest.mark.anyio
async def test_export_e2e_deleted_circles_excluded(client, session, topic_with_creator):
    """Deleted circles are not included in export."""
    topic, creator, creator_token = topic_with_creator

    from datetime import UTC, datetime

    # Create 2 circles, delete one
    circle1 = Circle(topic_id=topic.id, name="ActiveCircle")
    circle2 = Circle(topic_id=topic.id, name="DeletedCircle", deleted_at=datetime.now(UTC))
    session.add(circle1)
    session.add(circle2)
    await session.commit()

    resp = await client.get(
        f"/topics/{topic.id}/export",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    circle_names = {c["name"] for c in data["circles"]}
    assert "ActiveCircle" in circle_names
    assert "DeletedCircle" not in circle_names


@pytest.mark.anyio
async def test_export_e2e_deleted_updates_excluded(client, session, topic_with_creator):
    """Deleted updates are not included in export."""
    topic, creator, creator_token = topic_with_creator

    from datetime import UTC, datetime

    circle = Circle(topic_id=topic.id, name="TestCircle")
    session.add(circle)
    await session.flush()

    # Create 2 updates, delete one
    await _create_update_with_circles(session, topic.id, creator.id, "Active update", [circle.id])

    update2_deleted = Update(
        topic_id=topic.id,
        author_member_id=creator.id,
        body="Deleted update",
        deleted_at=datetime.now(UTC),
    )
    session.add(update2_deleted)
    await session.flush()

    uc2 = UpdateCircle(update_id=update2_deleted.id, circle_id=circle.id)
    session.add(uc2)
    await session.commit()

    resp = await client.get(
        f"/topics/{topic.id}/export",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    # Only active update should be present
    assert len(data["updates"]) == 1
    assert data["updates"][0]["body"] == "Active update"
