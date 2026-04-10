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

"""Tests for audit remediation fixes (Tasks 1-19)."""

import pytest
from sqlmodel import select

from app.models.circle import Circle
from app.models.enums import MemberRole
from app.models.member import Member
from app.models.topic import Topic
from app.services.auth import generate_token
from app.services.member import promote_member

# --- Task 2: Token revocation actually works ---


@pytest.mark.anyio
async def test_revoke_token_endpoint_works(client, session, topic_with_creator):
    """C-1: POST /auth/revoke must actually revoke the token."""
    topic, creator, raw_token = topic_with_creator

    # Revoke the token
    resp = await client.post(
        "/auth/revoke",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert resp.status_code == 200

    # Subsequent request should fail
    resp = await client.get(
        f"/topics/{topic.id}",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert resp.status_code == 401


# --- Task 4: Cross-topic authorization ---


@pytest.mark.anyio
async def test_cross_topic_access_rejected(client, session):
    """H-1: A member from Topic A cannot access Topic B resources."""
    # Create two topics with creators
    topic_a = Topic(default_title="Topic A")
    topic_b = Topic(default_title="Topic B")
    session.add(topic_a)
    session.add(topic_b)
    await session.flush()

    member_a = Member(topic_id=topic_a.id, role=MemberRole.owner)
    session.add(member_a)
    await session.flush()

    token_a = await generate_token(session, member_a.id)
    await session.commit()

    # Try to access Topic B with Topic A's token
    resp = await client.get(
        f"/topics/{topic_b.id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 403


# --- Task 6: Invite role restriction ---


@pytest.mark.anyio
async def test_invite_rejects_admin_role(client, session, topic_with_creator):
    """H-4: Cannot invite with role=admin."""
    topic, creator, raw_token = topic_with_creator

    circle = Circle(topic_id=topic.id, name="Test")
    session.add(circle)
    await session.commit()

    resp = await client.post(
        f"/topics/{topic.id}/members",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={"email": "test@example.com", "circle_id": str(circle.id), "role": "admin"},
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_invite_rejects_creator_role(client, session, topic_with_creator):
    """H-4: Cannot invite with role=creator."""
    topic, creator, raw_token = topic_with_creator

    circle = Circle(topic_id=topic.id, name="Test")
    session.add(circle)
    await session.commit()

    resp = await client.post(
        f"/topics/{topic.id}/members",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={"email": "test@example.com", "circle_id": str(circle.id), "role": "creator"},
    )
    assert resp.status_code == 422


# --- Task 8: Block promotion to creator ---


@pytest.mark.anyio
async def test_promote_to_creator_rejected(session, topic_with_creator):
    """L-2: Cannot promote to creator via promote_member."""
    topic, creator, _ = topic_with_creator

    admin = Member(topic_id=topic.id, role=MemberRole.admin)
    session.add(admin)
    await session.flush()
    await session.commit()

    with pytest.raises(ValueError, match="Cannot promote to creator"):
        await promote_member(session, admin.id, MemberRole.owner, creator)


# --- Task 10: Input length validation ---


@pytest.mark.anyio
async def test_oversized_topic_title_rejected(client):
    """M-2: Topic title exceeding max_length returns 422."""
    resp = await client.post(
        "/topics",
        json={"default_title": "x" * 201},
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_empty_topic_title_rejected(client):
    """M-2: Empty topic title returns 422."""
    resp = await client.post(
        "/topics",
        json={"default_title": ""},
    )
    assert resp.status_code == 422


# --- Task 11: Soft-delete circles ---


@pytest.mark.anyio
async def test_circle_soft_delete(session, topic_with_creator):
    """M-4: Deleting a circle sets deleted_at instead of removing the row."""
    topic, creator, _ = topic_with_creator
    topic_id = topic.id

    circle = Circle(topic_id=topic_id, name="ToDelete")
    session.add(circle)
    await session.flush()
    circle_id = circle.id
    await session.commit()

    from app.services.circle import delete_circle, list_circles

    await delete_circle(session, circle_id, topic_id)
    await session.commit()

    # Verify deleted_at is set by re-fetching
    await session.flush()
    result = await session.execute(select(Circle).where(Circle.id == circle_id))
    deleted_circle = result.scalar_one()
    assert deleted_circle.deleted_at is not None

    # list_circles excludes soft-deleted
    circles = await list_circles(session, topic_id)
    assert all(c.id != circle_id for c in circles)


# --- Task 12: Clear scoped_title ---


@pytest.mark.anyio
async def test_clear_scoped_title(session, topic_with_creator):
    """M-3: Can clear scoped_title via clear_scoped_title flag."""
    topic, creator, _ = topic_with_creator

    circle = Circle(topic_id=topic.id, name="Test", scoped_title="Original")
    session.add(circle)
    await session.flush()
    await session.commit()

    from app.services.circle import rename_circle

    updated = await rename_circle(session, circle.id, topic.id, clear_scoped_title=True)
    assert updated.scoped_title is None


# --- Task 19: No raw token in create response ---


@pytest.mark.anyio
async def test_create_topic_no_raw_token(client):
    """L-1: TopicCreateResponse should not contain raw token."""
    resp = await client.post(
        "/topics",
        json={"default_title": "Test Topic"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "token" not in data
    assert "magic_link" in data
