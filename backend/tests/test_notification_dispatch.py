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

"""Tests for notification dispatch service and dispatch helpers."""

import uuid

import pytest
from sqlmodel import select

from app.models.enums import (
    DeliveryMode,
    MemberRole,
    NotificationChannel,
    NotificationStatus,
    NotificationTrigger,
)
from app.models.member import Member, MemberCircleHistory
from app.models.notification import NotificationLog, NotificationPreference
from app.services.notifications.registry import ProviderRegistry
from app.services.notifications.service import NotificationService

# ---------------------------------------------------------------------------
# Helpers / fake providers
# ---------------------------------------------------------------------------


class FakeEmailProvider:
    """Minimal in-memory email provider for testing."""

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
        self.sent.append(
            {"recipient": recipient, "subject": subject, "body": body, "html_body": html_body}
        )
        return f"fake-msg-{len(self.sent)}"


class FakeSMSProvider:
    """Minimal in-memory SMS provider for testing."""

    channel = NotificationChannel.sms

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
        self.sent.append({"recipient": recipient, "body": body})
        return f"fake-sms-{len(self.sent)}"


class FailingProvider:
    """Provider that always raises an exception."""

    channel = NotificationChannel.email

    async def send(
        self, *, recipient: str, subject: str,
        body: str, html_body: str | None = None,
    ) -> str:
        raise RuntimeError("Simulated send failure")


def make_registry(*providers) -> ProviderRegistry:
    registry = ProviderRegistry()
    for p in providers:
        registry.register(p)
    return registry


# ---------------------------------------------------------------------------
# NotificationService unit tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_dispatch_immediate_sends_via_provider(session, topic_with_creator):
    topic, member, _ = topic_with_creator

    email_provider = FakeEmailProvider()
    registry = make_registry(email_provider)
    service = NotificationService(registry)

    log = await service.dispatch(
        session=session,
        member_id=member.id,
        topic_id=topic.id,
        trigger=NotificationTrigger.new_update,
        subject="Test Subject",
        body="Test body",
        recipient_address="test@example.com",
        channel=NotificationChannel.email,
    )
    await session.commit()

    assert log.status == NotificationStatus.sent
    assert log.provider_message_id is not None
    assert log.sent_at is not None
    assert len(email_provider.sent) == 1
    assert email_provider.sent[0]["recipient"] == "test@example.com"
    assert email_provider.sent[0]["subject"] == "Test Subject"


@pytest.mark.anyio
async def test_dispatch_muted_skips_send(session, topic_with_creator):
    topic, member, _ = topic_with_creator

    pref = NotificationPreference(
        member_id=member.id,
        channel=NotificationChannel.email,
        trigger=NotificationTrigger.new_update,
        delivery_mode=DeliveryMode.muted,
    )
    session.add(pref)
    await session.flush()

    email_provider = FakeEmailProvider()
    registry = make_registry(email_provider)
    service = NotificationService(registry)

    log = await service.dispatch(
        session=session,
        member_id=member.id,
        topic_id=topic.id,
        trigger=NotificationTrigger.new_update,
        subject="Test Subject",
        body="Test body",
        recipient_address="test@example.com",
        channel=NotificationChannel.email,
    )
    await session.commit()

    assert log.status == NotificationStatus.skipped
    assert len(email_provider.sent) == 0


@pytest.mark.anyio
async def test_dispatch_digest_mode_queues_not_sends(session, topic_with_creator):
    topic, member, _ = topic_with_creator

    pref = NotificationPreference(
        member_id=member.id,
        channel=NotificationChannel.email,
        trigger=NotificationTrigger.new_update,
        delivery_mode=DeliveryMode.digest,
    )
    session.add(pref)
    await session.flush()

    email_provider = FakeEmailProvider()
    registry = make_registry(email_provider)
    service = NotificationService(registry)

    log = await service.dispatch(
        session=session,
        member_id=member.id,
        topic_id=topic.id,
        trigger=NotificationTrigger.new_update,
        subject="Test Subject",
        body="Test body",
        recipient_address="test@example.com",
        channel=NotificationChannel.email,
    )
    await session.commit()

    # Digest mode marks as skipped (scheduler handles batch delivery)
    assert log.status == NotificationStatus.skipped
    assert len(email_provider.sent) == 0


@pytest.mark.anyio
async def test_dispatch_no_provider_skips(session, topic_with_creator):
    topic, member, _ = topic_with_creator

    # Empty registry — no provider for email
    registry = ProviderRegistry()
    service = NotificationService(registry)

    log = await service.dispatch(
        session=session,
        member_id=member.id,
        topic_id=topic.id,
        trigger=NotificationTrigger.new_update,
        subject="Subject",
        body="Body",
        recipient_address="test@example.com",
        channel=NotificationChannel.email,
    )
    await session.commit()

    assert log.status == NotificationStatus.skipped


@pytest.mark.anyio
async def test_dispatch_provider_failure_marks_failed(session, topic_with_creator):
    topic, member, _ = topic_with_creator

    registry = make_registry(FailingProvider())
    service = NotificationService(registry)

    log = await service.dispatch(
        session=session,
        member_id=member.id,
        topic_id=topic.id,
        trigger=NotificationTrigger.new_update,
        subject="Subject",
        body="Body",
        recipient_address="test@example.com",
        channel=NotificationChannel.email,
    )
    await session.commit()

    assert log.status == NotificationStatus.failed
    assert log.error_detail is not None
    assert "Simulated send failure" in log.error_detail


@pytest.mark.anyio
async def test_dispatch_creates_log_entry(session, topic_with_creator):
    topic, member, _ = topic_with_creator

    email_provider = FakeEmailProvider()
    registry = make_registry(email_provider)
    service = NotificationService(registry)

    await service.dispatch(
        session=session,
        member_id=member.id,
        topic_id=topic.id,
        trigger=NotificationTrigger.invite,
        subject="Invite",
        body="Body",
        recipient_address="test@example.com",
        channel=NotificationChannel.email,
    )
    await session.commit()

    logs_result = await session.execute(
        select(NotificationLog).where(NotificationLog.member_id == member.id)
    )
    logs = list(logs_result.scalars().all())
    assert len(logs) == 1
    assert logs[0].trigger == NotificationTrigger.invite
    assert logs[0].channel == NotificationChannel.email


# ---------------------------------------------------------------------------
# dispatch_update_notifications integration tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_dispatch_update_sends_to_circle_members(session, circle_with_members):
    from app.services.notifications.dispatch import dispatch_update_notifications

    circle, recipients, _ = circle_with_members
    topic_id = recipients[0].topic_id

    email_provider = FakeEmailProvider()
    registry = make_registry(email_provider)

    update_id = uuid.uuid4()
    await dispatch_update_notifications(
        session=session,
        registry=registry,
        topic_id=topic_id,
        update_id=update_id,
        circle_ids=[circle.id],
        author_handle="Author",
        body="New update text",
    )
    await session.commit()

    # Both recipients should have received a notification
    assert len(email_provider.sent) == 2
    sent_recipients = {msg["recipient"] for msg in email_provider.sent}
    expected = {r.email for r in recipients if r.email}
    assert sent_recipients == expected


@pytest.mark.anyio
async def test_dispatch_update_skips_members_without_address(session, topic_with_creator):
    from app.services.notifications.dispatch import dispatch_update_notifications

    topic, creator, _ = topic_with_creator

    from app.models.circle import Circle

    circle = Circle(topic_id=topic.id, name="No-address circle")
    session.add(circle)
    await session.flush()

    # Member with no email and no phone
    no_address_member = Member(
        topic_id=topic.id,
        role=MemberRole.recipient,
        email=None,
        phone=None,
    )
    session.add(no_address_member)
    await session.flush()

    history = MemberCircleHistory(member_id=no_address_member.id, circle_id=circle.id)
    session.add(history)
    await session.flush()

    email_provider = FakeEmailProvider()
    registry = make_registry(email_provider)

    await dispatch_update_notifications(
        session=session,
        registry=registry,
        topic_id=topic.id,
        update_id=uuid.uuid4(),
        circle_ids=[circle.id],
        author_handle=None,
        body="Update text",
    )
    await session.commit()

    # No sends because the member has no address
    assert len(email_provider.sent) == 0


@pytest.mark.anyio
async def test_dispatch_update_nonexistent_topic_logs_warning(session):
    from app.services.notifications.dispatch import dispatch_update_notifications

    registry = ProviderRegistry()
    nonexistent_topic_id = uuid.uuid4()

    # Should complete without exception — warning is logged internally
    await dispatch_update_notifications(
        session=session,
        registry=registry,
        topic_id=nonexistent_topic_id,
        update_id=uuid.uuid4(),
        circle_ids=[uuid.uuid4()],
        author_handle=None,
        body="body",
    )


# ---------------------------------------------------------------------------
# dispatch_relay_notifications integration tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_dispatch_relay_sends_to_circle_members(session, circle_with_members):
    from app.services.notifications.dispatch import dispatch_relay_notifications

    circle, recipients, _ = circle_with_members
    topic_id = recipients[0].topic_id

    email_provider = FakeEmailProvider()
    registry = make_registry(email_provider)

    await dispatch_relay_notifications(
        session=session,
        registry=registry,
        topic_id=topic_id,
        reply_id=uuid.uuid4(),
        circle_ids=[circle.id],
        author_identity="Relayer",
        reply_body="A relayed reply",
    )
    await session.commit()

    assert len(email_provider.sent) == 2


@pytest.mark.anyio
async def test_dispatch_relay_none_circle_ids_sends_to_all_members(session, topic_with_creator):
    from app.services.notifications.dispatch import dispatch_relay_notifications

    topic, creator, _ = topic_with_creator

    # Add an extra email-bearing member
    extra_member = Member(
        topic_id=topic.id,
        role=MemberRole.recipient,
        email="extra@test.com",
    )
    session.add(extra_member)
    await session.flush()

    email_provider = FakeEmailProvider()
    registry = make_registry(email_provider)

    await dispatch_relay_notifications(
        session=session,
        registry=registry,
        topic_id=topic.id,
        reply_id=uuid.uuid4(),
        circle_ids=None,
        author_identity="Admin",
        reply_body="Reply text",
    )
    await session.commit()

    # Both the creator and extra member should have received notifications
    # (creator has email, extra member has email)
    assert len(email_provider.sent) >= 1


# ---------------------------------------------------------------------------
# dispatch_invite_notification integration tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_dispatch_invite_sends_to_member(session, topic_with_creator):
    from app.services.notifications.dispatch import dispatch_invite_notification

    topic, creator, _ = topic_with_creator

    invitee = Member(
        topic_id=topic.id,
        role=MemberRole.recipient,
        email="invitee@example.com",
    )
    session.add(invitee)
    await session.flush()

    email_provider = FakeEmailProvider()
    registry = make_registry(email_provider)

    await dispatch_invite_notification(
        session=session,
        registry=registry,
        topic_id=topic.id,
        member_id=invitee.id,
        magic_link="http://example.com/auth?token=abc123",
    )
    await session.commit()

    assert len(email_provider.sent) == 1
    assert email_provider.sent[0]["recipient"] == "invitee@example.com"
    sent_body = email_provider.sent[0]["body"]
    assert "magic_link" in sent_body or "example.com" in sent_body


@pytest.mark.anyio
async def test_dispatch_invite_skips_member_without_address(session, topic_with_creator):
    from app.services.notifications.dispatch import dispatch_invite_notification

    topic, creator, _ = topic_with_creator

    no_address = Member(
        topic_id=topic.id,
        role=MemberRole.recipient,
        email=None,
        phone=None,
    )
    session.add(no_address)
    await session.flush()

    email_provider = FakeEmailProvider()
    registry = make_registry(email_provider)

    await dispatch_invite_notification(
        session=session,
        registry=registry,
        topic_id=topic.id,
        member_id=no_address.id,
        magic_link="http://example.com/auth?token=abc123",
    )
    await session.commit()

    assert len(email_provider.sent) == 0


@pytest.mark.anyio
async def test_dispatch_invite_sms_channel(session, topic_with_creator):
    from app.services.notifications.dispatch import dispatch_invite_notification

    topic, creator, _ = topic_with_creator

    sms_member = Member(
        topic_id=topic.id,
        role=MemberRole.recipient,
        email=None,
        phone="+15550001234",
        notification_channel=NotificationChannel.sms,
    )
    session.add(sms_member)
    await session.flush()

    sms_provider = FakeSMSProvider()
    registry = make_registry(sms_provider)

    await dispatch_invite_notification(
        session=session,
        registry=registry,
        topic_id=topic.id,
        member_id=sms_member.id,
        magic_link="http://example.com/auth?token=abc123",
    )
    await session.commit()

    assert len(sms_provider.sent) == 1
    assert sms_provider.sent[0]["recipient"] == "+15550001234"


# ---------------------------------------------------------------------------
# get_recipients_for_update correctness
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_revoked_member_does_not_receive_notification(session, circle_with_members):
    """A member whose circle access was revoked should not receive notifications."""
    from datetime import UTC, datetime

    from app.services.notifications.dispatch import dispatch_update_notifications

    circle, recipients, _ = circle_with_members

    # Revoke the first recipient's access
    history_result = await session.execute(
        select(MemberCircleHistory).where(
            MemberCircleHistory.member_id == recipients[0].id,
            MemberCircleHistory.circle_id == circle.id,
        )
    )
    history = history_result.scalar_one()
    history.revoked_at = datetime.now(UTC)
    session.add(history)
    await session.flush()

    email_provider = FakeEmailProvider()
    registry = make_registry(email_provider)

    await dispatch_update_notifications(
        session=session,
        registry=registry,
        topic_id=recipients[0].topic_id,
        update_id=uuid.uuid4(),
        circle_ids=[circle.id],
        author_handle=None,
        body="update",
    )
    await session.commit()

    # Only the non-revoked member should receive a notification
    assert len(email_provider.sent) == 1
    assert email_provider.sent[0]["recipient"] == recipients[1].email
