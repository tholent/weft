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

"""Regression tests for Wave 2 audit remediation (Tasks 7-10)."""

import uuid
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from sqlmodel import select

from app.models.attachment import Attachment
from app.models.circle import Circle
from app.models.enums import (
    DeliveryMode,
    MemberRole,
    NotificationChannel,
    NotificationStatus,
    NotificationTrigger,
)
from app.models.member import Member
from app.models.notification import NotificationLog, NotificationPreference
from app.models.update import Update
from app.schemas.member import MemberInvite
from app.services.export import export_topic
from app.services.notifications.registry import ProviderRegistry
from app.services.notifications.service import NotificationService

# ---------------------------------------------------------------------------
# Task 7 — E.164 phone validation
# ---------------------------------------------------------------------------


class TestE164PhoneValidation:
    """MemberInvite rejects any phone number not in strict E.164 format."""

    def _valid_invite(self, **kwargs) -> MemberInvite:
        base = {
            "circle_id": uuid.uuid4(),
            "role": MemberRole.recipient,
        }
        base.update(kwargs)
        return MemberInvite(**base)

    def test_valid_us_number_accepted(self):
        invite = self._valid_invite(phone="+14155552671")
        assert invite.phone == "+14155552671"

    def test_valid_uk_number_accepted(self):
        invite = self._valid_invite(phone="+447700900123")
        assert invite.phone == "+447700900123"

    def test_valid_short_number_accepted(self):
        # Minimum: + followed by 2 digits (country code 1 + 1 subscriber digit)
        invite = self._valid_invite(phone="+12")
        assert invite.phone == "+12"

    def test_none_phone_accepted(self):
        invite = self._valid_invite(phone=None)
        assert invite.phone is None

    def test_missing_plus_prefix_rejected(self):
        with pytest.raises(ValidationError, match="E.164"):
            self._valid_invite(phone="14155552671")

    def test_plus_only_rejected(self):
        with pytest.raises(ValidationError):
            self._valid_invite(phone="+")

    def test_leading_zero_country_code_rejected(self):
        # +0... is not valid E.164 (country codes start at 1)
        with pytest.raises(ValidationError, match="E.164"):
            self._valid_invite(phone="+01234567890")

    def test_too_long_rejected(self):
        # E.164 max is 15 digits total; 16 digits total is over the limit
        # Regex allows \+[1-9]\d{1,14}, so maximum is + followed by 15 digits.
        # +1 followed by 15 more digits = 16 digits total → rejected.
        with pytest.raises(ValidationError, match="E.164"):
            self._valid_invite(phone="+1" + "2" * 15)  # + 1 + 15 digits = 16 digits total

    def test_non_digit_characters_rejected(self):
        with pytest.raises(ValidationError, match="E.164"):
            self._valid_invite(phone="+1415-555-2671")

    def test_spaces_rejected(self):
        with pytest.raises(ValidationError, match="E.164"):
            self._valid_invite(phone="+1 415 555 2671")

    def test_empty_string_rejected(self):
        with pytest.raises(ValidationError, match="E.164"):
            self._valid_invite(phone="")


# ---------------------------------------------------------------------------
# Task 8 — secrets-based short code generation
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_generate_short_code_uses_secrets(session):
    """generate_short_code returns 3-char uppercase alphanumeric codes."""
    from app.services.topic import generate_short_code

    code = await generate_short_code(session)

    assert len(code) == 3
    assert code.isupper() or code.isdigit() or all(c.isalnum() for c in code)
    # All chars must be uppercase letters or digits
    import string

    valid_chars = set(string.ascii_uppercase + string.digits)
    assert all(c in valid_chars for c in code)


@pytest.mark.anyio
async def test_generate_short_code_is_not_random_module(session):
    """generate_short_code must not use the random module (uses secrets)."""
    import importlib

    source = importlib.util.find_spec("app.services.topic")
    assert source is not None
    with open(source.origin) as f:
        source_text = f.read()
    assert "import random" not in source_text
    assert "random.choices" not in source_text
    assert "secrets" in source_text


# ---------------------------------------------------------------------------
# Task 9 — Digest notification pipeline
# ---------------------------------------------------------------------------


class FakeEmailProvider:
    channel = NotificationChannel.email

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(
        self,
        *,
        recipient: str,
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> str:
        self.sent.append({"recipient": recipient, "subject": subject, "body": body})
        return f"fake-msg-{len(self.sent)}"


@pytest.mark.anyio
async def test_digest_mode_creates_pending_digest_log(session, topic_with_creator):
    """Member with digest preference gets status=pending_digest, not skipped."""
    topic, creator, _ = topic_with_creator

    member = Member(topic_id=topic.id, role=MemberRole.recipient, email="digest@test.com")
    session.add(member)
    await session.flush()

    # Set digest preference for new_update trigger
    pref = NotificationPreference(
        member_id=member.id,
        channel=NotificationChannel.email,
        trigger=NotificationTrigger.new_update,
        delivery_mode=DeliveryMode.digest,
    )
    session.add(pref)
    await session.flush()

    provider = FakeEmailProvider()
    registry = ProviderRegistry()
    registry.register(provider)
    svc = NotificationService(registry)

    log = await svc.dispatch(
        session=session,
        member_id=member.id,
        topic_id=topic.id,
        trigger=NotificationTrigger.new_update,
        subject="Test subject",
        body="Test body",
        recipient_address="digest@test.com",
        channel=NotificationChannel.email,
    )

    assert log.status == NotificationStatus.pending_digest
    # Provider must NOT have been called for digest-mode members
    assert len(provider.sent) == 0


@pytest.mark.anyio
async def test_immediate_mode_not_affected_by_digest_changes(session, topic_with_creator):
    """Members in immediate mode still get sent status immediately."""
    topic, creator, _ = topic_with_creator

    member = Member(topic_id=topic.id, role=MemberRole.recipient, email="immediate@test.com")
    session.add(member)
    await session.flush()

    # Immediate preference
    pref = NotificationPreference(
        member_id=member.id,
        channel=NotificationChannel.email,
        trigger=NotificationTrigger.new_update,
        delivery_mode=DeliveryMode.immediate,
    )
    session.add(pref)
    await session.flush()

    provider = FakeEmailProvider()
    registry = ProviderRegistry()
    registry.register(provider)
    svc = NotificationService(registry)

    log = await svc.dispatch(
        session=session,
        member_id=member.id,
        topic_id=topic.id,
        trigger=NotificationTrigger.new_update,
        subject="Test subject",
        body="Test body",
        recipient_address="immediate@test.com",
        channel=NotificationChannel.email,
    )

    assert log.status == NotificationStatus.sent
    assert len(provider.sent) == 1


@pytest.mark.anyio
async def test_digest_task_processes_pending_digest_logs(session, topic_with_creator):
    """digest_notification_task picks up pending_digest logs and marks them sent."""
    from app.config import Settings
    from app.scheduler.tasks import digest_notification_task

    topic, creator, _ = topic_with_creator

    member = Member(topic_id=topic.id, role=MemberRole.recipient, email="digest-task@test.com")
    session.add(member)
    await session.flush()

    # Digest preference
    pref = NotificationPreference(
        member_id=member.id,
        channel=NotificationChannel.email,
        trigger=NotificationTrigger.new_update,
        delivery_mode=DeliveryMode.digest,
    )
    session.add(pref)

    # Manually create a pending_digest log (simulating what the service writes)
    log = NotificationLog(
        member_id=member.id,
        topic_id=topic.id,
        channel=NotificationChannel.email,
        trigger=NotificationTrigger.new_update,
        status=NotificationStatus.pending_digest,
    )
    session.add(log)
    await session.commit()

    provider = FakeEmailProvider()
    fake_registry = ProviderRegistry()
    fake_registry.register(provider)

    # Patch create_registry and async_session_factory so the task uses our test DB
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    engine = session.bind  # reuse the test engine

    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    with (
        patch("app.scheduler.tasks.create_registry", return_value=fake_registry),
        patch(
            "app.scheduler.tasks.get_settings",
            return_value=Settings(
                database_url="sqlite+aiosqlite:///./test.db",
                secret_key="test-secret",
                resend_api_key="",
                base_url="http://localhost:5173",
            ),
        ),
        patch("app.scheduler.tasks.async_session_factory", sf),
    ):
        await digest_notification_task()

    # Re-query the log to verify it was updated
    async with sf() as verify_session:
        result = await verify_session.execute(
            select(NotificationLog).where(NotificationLog.id == log.id)
        )
        updated_log = result.scalar_one()

    assert updated_log.status == NotificationStatus.sent
    assert len(provider.sent) == 1


@pytest.mark.anyio
async def test_digest_task_ignores_plain_pending_logs(session, topic_with_creator):
    """digest_notification_task does NOT process status=pending logs."""
    from app.config import Settings
    from app.scheduler.tasks import digest_notification_task

    topic, creator, _ = topic_with_creator

    member = Member(topic_id=topic.id, role=MemberRole.recipient, email="pending-only@test.com")
    session.add(member)
    await session.flush()

    # Digest preference
    pref = NotificationPreference(
        member_id=member.id,
        channel=NotificationChannel.email,
        trigger=NotificationTrigger.new_update,
        delivery_mode=DeliveryMode.digest,
    )
    session.add(pref)

    # Create a plain pending log (as might have existed before the fix)
    log = NotificationLog(
        member_id=member.id,
        topic_id=topic.id,
        channel=NotificationChannel.email,
        trigger=NotificationTrigger.new_update,
        status=NotificationStatus.pending,
    )
    session.add(log)
    await session.commit()

    provider = FakeEmailProvider()
    fake_registry = ProviderRegistry()
    fake_registry.register(provider)

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    engine = session.bind
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    with (
        patch("app.scheduler.tasks.create_registry", return_value=fake_registry),
        patch(
            "app.scheduler.tasks.get_settings",
            return_value=Settings(
                database_url="sqlite+aiosqlite:///./test.db",
                secret_key="test-secret",
                resend_api_key="",
                base_url="http://localhost:5173",
            ),
        ),
        patch("app.scheduler.tasks.async_session_factory", sf),
    ):
        await digest_notification_task()

    # Plain pending logs must remain untouched
    async with sf() as verify_session:
        result = await verify_session.execute(
            select(NotificationLog).where(NotificationLog.id == log.id)
        )
        unchanged_log = result.scalar_one()

    assert unchanged_log.status == NotificationStatus.pending
    assert len(provider.sent) == 0


# ---------------------------------------------------------------------------
# Task 10 — storage_key scrubbed from export
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_export_excludes_storage_key(session, topic_with_creator):
    """Attachment export dict must NOT contain storage_key."""
    topic, creator, _ = topic_with_creator

    # Create a circle and update
    circle = Circle(topic_id=topic.id, name="Test Circle")
    session.add(circle)
    await session.flush()

    update = Update(topic_id=topic.id, author_member_id=creator.id, body="Update with attachment")
    session.add(update)
    await session.flush()

    # Create an attachment with a storage_key
    attachment = Attachment(
        update_id=update.id,
        topic_id=topic.id,
        filename="photo.jpg",
        content_type="image/jpeg",
        storage_key="s3://bucket/private/key/photo.jpg",
        size_bytes=204800,
    )
    session.add(attachment)
    await session.commit()

    result = await export_topic(session, topic.id)

    updates_data = result["updates"]
    assert len(updates_data) == 1
    attachments_data = updates_data[0]["attachments"]
    assert len(attachments_data) == 1

    att_export = attachments_data[0]
    # storage_key must not be present at all
    assert "storage_key" not in att_export
    # Public-safe fields must be present
    assert att_export["filename"] == "photo.jpg"
    assert att_export["content_type"] == "image/jpeg"
    assert att_export["size_bytes"] == 204800


@pytest.mark.anyio
async def test_export_storage_key_not_in_raw_json(client, session, topic_with_creator):
    """The raw export JSON response must not contain any storage_key substring."""
    topic, creator, creator_token = topic_with_creator

    circle = Circle(topic_id=topic.id, name="Test Circle")
    session.add(circle)
    await session.flush()

    update = Update(topic_id=topic.id, author_member_id=creator.id, body="Attachment test update")
    session.add(update)
    await session.flush()

    attachment = Attachment(
        update_id=update.id,
        topic_id=topic.id,
        filename="secret.pdf",
        content_type="application/pdf",
        storage_key="s3://internal-bucket/org-secret/secret.pdf",
        size_bytes=1024,
    )
    session.add(attachment)
    await session.commit()

    resp = await client.get(
        f"/topics/{topic.id}/export",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    raw = resp.text
    assert "storage_key" not in raw
    assert "s3://internal-bucket" not in raw
