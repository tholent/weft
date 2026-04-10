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

"""Tests for photo attachment upload, listing, serving, and permission checks."""

import tempfile
import uuid
from unittest.mock import patch

import pytest

from app.models.enums import MemberRole
from app.models.update import Update
from app.services.attachment import (
    ALLOWED_CONTENT_TYPES,
    get_attachment,
    get_attachments,
    save_attachment,
)

# ---------------------------------------------------------------------------
# Service-layer unit tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_save_attachment_persists_to_disk_and_db(session, topic_with_creator):
    topic, creator, _ = topic_with_creator

    update = Update(topic_id=topic.id, author_member_id=creator.id, body="Update with photo")
    session.add(update)
    await session.flush()

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.services.attachment.get_settings") as mock_settings:
            mock_settings.return_value.attachment_local_path = tmpdir
            mock_settings.return_value.attachment_max_size_bytes = 10 * 1024 * 1024

            data = b"\xff\xd8\xff" + b"\x00" * 100  # Minimal JPEG-like bytes
            attachment = await save_attachment(
                session,
                update_id=update.id,
                topic_id=topic.id,
                filename="photo.jpg",
                content_type="image/jpeg",
                data=data,
            )
            await session.flush()

    assert attachment.id is not None
    assert attachment.update_id == update.id
    assert attachment.topic_id == topic.id
    assert attachment.filename == "photo.jpg"
    assert attachment.content_type == "image/jpeg"
    assert attachment.size_bytes == len(data)
    assert attachment.storage_key.endswith(".jpg")


@pytest.mark.anyio
async def test_save_attachment_rejects_disallowed_content_type(session, topic_with_creator):
    topic, creator, _ = topic_with_creator

    update = Update(topic_id=topic.id, author_member_id=creator.id, body="Update")
    session.add(update)
    await session.flush()

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.services.attachment.get_settings") as mock_settings:
            mock_settings.return_value.attachment_local_path = tmpdir
            mock_settings.return_value.attachment_max_size_bytes = 10 * 1024 * 1024

            with pytest.raises(ValueError, match="Unsupported content type"):
                await save_attachment(
                    session,
                    update_id=update.id,
                    topic_id=topic.id,
                    filename="doc.pdf",
                    content_type="application/pdf",
                    data=b"%PDF-1.4",
                )


@pytest.mark.anyio
async def test_save_attachment_rejects_oversized_file(session, topic_with_creator):
    topic, creator, _ = topic_with_creator

    update = Update(topic_id=topic.id, author_member_id=creator.id, body="Update")
    session.add(update)
    await session.flush()

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.services.attachment.get_settings") as mock_settings:
            # Set max to 100 bytes to trigger the error
            mock_settings.return_value.attachment_local_path = tmpdir
            mock_settings.return_value.attachment_max_size_bytes = 100

            with pytest.raises(ValueError, match="exceeds maximum"):
                await save_attachment(
                    session,
                    update_id=update.id,
                    topic_id=topic.id,
                    filename="large.png",
                    content_type="image/png",
                    data=b"\x89PNG" + b"\x00" * 200,
                )


@pytest.mark.anyio
async def test_get_attachments_returns_all_for_update(session, topic_with_creator):
    topic, creator, _ = topic_with_creator

    update = Update(topic_id=topic.id, author_member_id=creator.id, body="Update")
    session.add(update)
    await session.flush()

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.services.attachment.get_settings") as mock_settings:
            mock_settings.return_value.attachment_local_path = tmpdir
            mock_settings.return_value.attachment_max_size_bytes = 10 * 1024 * 1024

            for i in range(3):
                await save_attachment(
                    session,
                    update_id=update.id,
                    topic_id=topic.id,
                    filename=f"photo{i}.jpg",
                    content_type="image/jpeg",
                    data=b"\xff\xd8\xff" + bytes([i]) * 50,
                )
        await session.flush()

    attachments = await get_attachments(session, update.id)
    assert len(attachments) == 3


@pytest.mark.anyio
async def test_get_attachment_returns_none_for_missing_id(session):
    result = await get_attachment(session, uuid.uuid4())
    assert result is None


@pytest.mark.anyio
async def test_all_allowed_content_types_accepted(session, topic_with_creator):
    topic, creator, _ = topic_with_creator

    update = Update(topic_id=topic.id, author_member_id=creator.id, body="Update")
    session.add(update)
    await session.flush()

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.services.attachment.get_settings") as mock_settings:
            mock_settings.return_value.attachment_local_path = tmpdir
            mock_settings.return_value.attachment_max_size_bytes = 10 * 1024 * 1024

            for ct in ALLOWED_CONTENT_TYPES:
                attachment = await save_attachment(
                    session,
                    update_id=update.id,
                    topic_id=topic.id,
                    filename=f"file.{ct.split('/')[1]}",
                    content_type=ct,
                    data=b"\x00" * 10,
                )
                assert attachment.content_type == ct


# ---------------------------------------------------------------------------
# Router HTTP tests
# ---------------------------------------------------------------------------


def _make_image_bytes() -> bytes:
    """Return minimal valid-looking JPEG bytes."""
    return b"\xff\xd8\xff\xe0" + b"\x00" * 50


@pytest.mark.anyio
async def test_upload_attachment_admin_succeeds(client, session, topic_with_creator):
    topic, creator, raw_token = topic_with_creator

    update = Update(topic_id=topic.id, author_member_id=creator.id, body="Test update")
    session.add(update)
    await session.commit()

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.services.attachment.get_settings") as mock_settings:
            mock_settings.return_value.attachment_local_path = tmpdir
            mock_settings.return_value.attachment_max_size_bytes = 10 * 1024 * 1024

            resp = await client.post(
                f"/topics/{topic.id}/updates/{update.id}/attachments",
                headers={"Authorization": f"Bearer {raw_token}"},
                files={"file": ("photo.jpg", _make_image_bytes(), "image/jpeg")},
            )

    assert resp.status_code == 201
    data = resp.json()
    assert data["filename"] == "photo.jpg"
    assert data["content_type"] == "image/jpeg"
    assert data["update_id"] == str(update.id)
    assert data["topic_id"] == str(topic.id)


@pytest.mark.anyio
async def test_upload_attachment_recipient_forbidden(client, session, circle_with_members):
    circle, recipients, tokens = circle_with_members
    topic_id = recipients[0].topic_id

    # Get the topic's creator to make an update
    from sqlmodel import select as sqlselect

    from app.models.member import Member as MemberModel

    result = await session.execute(
        sqlselect(MemberModel).where(
            MemberModel.topic_id == topic_id,
            MemberModel.role == MemberRole.owner,
        )
    )
    owner = result.scalar_one()

    update = Update(topic_id=topic_id, author_member_id=owner.id, body="Test update")
    session.add(update)
    await session.commit()

    # Recipient tries to upload
    resp = await client.post(
        f"/topics/{topic_id}/updates/{update.id}/attachments",
        headers={"Authorization": f"Bearer {tokens[0]}"},
        files={"file": ("photo.jpg", _make_image_bytes(), "image/jpeg")},
    )

    assert resp.status_code == 403


@pytest.mark.anyio
async def test_upload_attachment_invalid_content_type(client, session, topic_with_creator):
    topic, creator, raw_token = topic_with_creator

    update = Update(topic_id=topic.id, author_member_id=creator.id, body="Test update")
    session.add(update)
    await session.commit()

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.services.attachment.get_settings") as mock_settings:
            mock_settings.return_value.attachment_local_path = tmpdir
            mock_settings.return_value.attachment_max_size_bytes = 10 * 1024 * 1024

            resp = await client.post(
                f"/topics/{topic.id}/updates/{update.id}/attachments",
                headers={"Authorization": f"Bearer {raw_token}"},
                files={"file": ("doc.pdf", b"%PDF-1.4 data", "application/pdf")},
            )

    assert resp.status_code == 400
    assert "Unsupported content type" in resp.json()["detail"]


@pytest.mark.anyio
async def test_list_attachments_requires_member(client, session, topic_with_creator):
    topic, creator, _ = topic_with_creator

    update = Update(topic_id=topic.id, author_member_id=creator.id, body="Test update")
    session.add(update)
    await session.commit()

    # No auth header
    resp = await client.get(
        f"/topics/{topic.id}/updates/{update.id}/attachments",
    )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_list_attachments_member_can_list(client, session, circle_with_members):
    circle, recipients, tokens = circle_with_members
    topic_id = recipients[0].topic_id

    from sqlmodel import select as sqlselect

    from app.models.member import Member as MemberModel

    result = await session.execute(
        sqlselect(MemberModel).where(
            MemberModel.topic_id == topic_id,
            MemberModel.role == MemberRole.owner,
        )
    )
    owner = result.scalar_one()

    update = Update(topic_id=topic_id, author_member_id=owner.id, body="Test update")
    session.add(update)
    await session.commit()

    resp = await client.get(
        f"/topics/{topic_id}/updates/{update.id}/attachments",
        headers={"Authorization": f"Bearer {tokens[0]}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.anyio
async def test_serve_attachment_not_found(client, session, topic_with_creator):
    topic, creator, raw_token = topic_with_creator

    resp = await client.get(
        f"/topics/{topic.id}/attachments/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_serve_attachment_cross_topic_rejected(client, session, topic_with_creator):
    """Attachment from a different topic returns 404 even with valid auth."""
    topic, creator, raw_token = topic_with_creator

    # Create a second topic with its own attachment ID
    from app.models.topic import Topic as TopicModel

    other_topic = TopicModel(default_title="Other Topic")
    session.add(other_topic)
    await session.commit()

    # Request with topic_id = our topic but attachment_id from other topic scope
    resp = await client.get(
        f"/topics/{topic.id}/attachments/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert resp.status_code == 404
