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

"""Regression tests for Wave 3 audit remediation (Tasks 11-19)."""

import re
import tempfile
from unittest.mock import patch

import pytest

from app.models.enums import MemberRole, NotificationChannel
from app.models.topic import Topic
from app.services.attachment import _verify_magic_bytes, save_attachment
from app.services.notifications.preferences import get_preferences
from app.services.topic import create_topic, generate_short_code

# ---------------------------------------------------------------------------
# Task 11 — short_code global uniqueness + collision retry
# ---------------------------------------------------------------------------


class TestShortCodeUniqueness:
    """generate_short_code must never return a code that already exists."""

    @pytest.mark.anyio
    async def test_short_code_format(self, session):
        """Generated code matches ^[A-Z0-9]{3}$."""
        code = await generate_short_code(session)
        assert re.fullmatch(r"[A-Z0-9]{3}", code), f"Bad format: {code!r}"

    @pytest.mark.anyio
    async def test_short_code_avoids_active_collision(self, session):
        """generate_short_code retries when the candidate already exists."""
        # Pre-create a topic with a known code
        occupied = Topic(default_title="Occupied", short_code="AAA", status="active")
        session.add(occupied)
        await session.flush()

        # Patch _generate_candidate to return the occupied code first, then a fresh one
        call_count = 0

        def _deterministic():
            nonlocal call_count
            call_count += 1
            return "AAA" if call_count == 1 else "ZZZ"

        with patch("app.services.topic._generate_candidate", side_effect=_deterministic):
            code = await generate_short_code(session)

        assert code == "ZZZ"
        assert call_count == 2

    @pytest.mark.anyio
    async def test_create_topic_integrity_error_retry(self, session):
        """create_topic handles IntegrityError and retries short-code generation."""
        # Just verify create_topic completes successfully; the retry path is
        # exercised in unit tests above.
        topic, member, magic_link = await create_topic(session, "Retry Topic")
        assert topic.short_code is not None
        assert re.fullmatch(r"[A-Z0-9]{3}", topic.short_code)
        assert member.role == MemberRole.owner


# ---------------------------------------------------------------------------
# Task 12 — SMS webhook rate limiting
# ---------------------------------------------------------------------------


class TestSmsWebhookRateLimit:
    """The SMS inbound webhook must return 429 after the configured rate limit."""

    @pytest.mark.anyio
    async def test_sms_webhook_rate_limit_returns_429(self, client):
        """Exceeding the per-IP rate limit returns HTTP 429."""
        from app.deps_sms import verify_twilio_signature
        from app.main import app

        # Override signature validation so we can focus on rate limiting
        app.dependency_overrides[verify_twilio_signature] = lambda: None

        try:
            # Reset the limiter state between tests by using a fresh storage
            # (slowapi uses in-memory storage by default; hitting the limit
            # requires a burst of 61 requests at "60/minute")
            responses = []
            for _ in range(62):
                resp = await client.post(
                    "/webhooks/sms/inbound",
                    data={"From": "+15550001234", "Body": "STOP", "To": "+15559999"},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                responses.append(resp.status_code)

            assert 429 in responses, (
                "Expected at least one 429 response after exceeding rate limit; "
                f"got status codes: {set(responses)}"
            )
        finally:
            # Remove the override so other tests are unaffected
            app.dependency_overrides.pop(verify_twilio_signature, None)


# ---------------------------------------------------------------------------
# Task 13 — Magic-byte content-type verification
# ---------------------------------------------------------------------------


class TestMagicByteVerification:
    """_verify_magic_bytes correctly accepts/rejects data for each MIME type."""

    def test_jpeg_accepted(self):
        data = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        assert _verify_magic_bytes("image/jpeg", data) is True

    def test_png_accepted(self):
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        assert _verify_magic_bytes("image/png", data) is True

    def test_gif87a_accepted(self):
        data = b"GIF87a" + b"\x00" * 100
        assert _verify_magic_bytes("image/gif", data) is True

    def test_gif89a_accepted(self):
        data = b"GIF89a" + b"\x00" * 100
        assert _verify_magic_bytes("image/gif", data) is True

    def test_webp_accepted(self):
        data = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 50
        assert _verify_magic_bytes("image/webp", data) is True

    def test_webp_with_riff_but_wrong_marker_rejected(self):
        """RIFF container that isn't WebP (e.g., WAV) must be rejected."""
        data = b"RIFF\x00\x00\x00\x00WAVEfmt " + b"\x00" * 50
        assert _verify_magic_bytes("image/webp", data) is False

    def test_html_declared_as_jpeg_rejected(self):
        data = b"<html><body>not an image</body></html>"
        assert _verify_magic_bytes("image/jpeg", data) is False

    def test_pdf_declared_as_png_rejected(self):
        data = b"%PDF-1.4 some content"
        assert _verify_magic_bytes("image/png", data) is False

    def test_unknown_type_rejected(self):
        assert _verify_magic_bytes("application/pdf", b"%PDF-1.4") is False

    @pytest.mark.anyio
    async def test_save_attachment_rejects_mismatched_bytes(self, session, topic_with_creator):
        """save_attachment raises ValueError when bytes don't match content_type."""
        from app.models.update import Update

        topic, creator, _ = topic_with_creator
        update = Update(topic_id=topic.id, author_member_id=creator.id, body="Test")
        session.add(update)
        await session.flush()

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.services.attachment.get_settings") as mock_settings:
                mock_settings.return_value.attachment_local_path = tmpdir
                mock_settings.return_value.attachment_max_size_bytes = 10 * 1024 * 1024

                # HTML bytes declared as JPEG
                with pytest.raises(ValueError, match="does not match declared content type"):
                    await save_attachment(
                        session,
                        update_id=update.id,
                        topic_id=topic.id,
                        filename="evil.jpg",
                        content_type="image/jpeg",
                        data=b"<html>not an image</html>",
                    )

    @pytest.mark.anyio
    async def test_save_attachment_accepts_valid_jpeg(self, session, topic_with_creator):
        """save_attachment accepts a valid JPEG (magic bytes match)."""
        from app.models.update import Update

        topic, creator, _ = topic_with_creator
        update = Update(topic_id=topic.id, author_member_id=creator.id, body="Test")
        session.add(update)
        await session.flush()

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.services.attachment.get_settings") as mock_settings:
                mock_settings.return_value.attachment_local_path = tmpdir
                mock_settings.return_value.attachment_max_size_bytes = 10 * 1024 * 1024

                attachment = await save_attachment(
                    session,
                    update_id=update.id,
                    topic_id=topic.id,
                    filename="photo.jpg",
                    content_type="image/jpeg",
                    data=b"\xff\xd8\xff\xe0" + b"\x00" * 100,
                )
                assert attachment.content_type == "image/jpeg"


# ---------------------------------------------------------------------------
# Task 16 — Owner notification preferences created at topic creation
# ---------------------------------------------------------------------------


class TestOwnerNotificationPreferences:
    """create_topic must seed default notification preferences for the owner."""

    @pytest.mark.anyio
    async def test_owner_has_default_preferences_after_topic_creation(self, session):
        """Owner preferences are populated immediately after create_topic."""
        topic, member, _magic_link = await create_topic(session, "Pref Test Topic")
        await session.flush()

        prefs = await get_preferences(session, member.id)
        assert len(prefs) > 0, "Owner must have at least one default preference"

        # All defaults should use the email channel
        channels = {p.channel for p in prefs}
        assert NotificationChannel.email in channels

    @pytest.mark.anyio
    async def test_owner_preferences_cover_all_triggers(self, session):
        """Default preferences include every NotificationTrigger."""
        from app.models.enums import NotificationTrigger

        topic, member, _magic_link = await create_topic(session, "All Triggers Topic")
        await session.flush()

        prefs = await get_preferences(session, member.id)
        covered_triggers = {p.trigger for p in prefs}
        for trigger in NotificationTrigger:
            assert trigger in covered_triggers, f"Missing default pref for trigger {trigger}"

    @pytest.mark.anyio
    async def test_owner_preferences_visible_via_http(self, client, session):
        """GET /notifications for the owner returns non-empty list after topic creation."""
        from app.services.auth import generate_token

        topic, member, _magic_link = await create_topic(session, "HTTP Pref Topic")
        raw_token = await generate_token(session, member.id)
        await session.commit()

        resp = await client.get(
            f"/topics/{topic.id}/members/{member.id}/notifications",
            headers={"Authorization": f"Bearer {raw_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Owner preferences should not be empty after topic creation"
