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

"""Unit tests for TwilioSMSProvider — exercises the exact wire format without
standing up the full dispatch pipeline."""

import base64
import json
import urllib.parse

import httpx
import pytest

from app.models.enums import NotificationChannel
from app.services.notifications.provider import NotificationProvider
from app.services.notifications.twilio_provider import TwilioSMSProvider


def _make_mock_transport(
    requests: list[httpx.Request],
    status_code: int,
    response_body: dict,  # type: ignore[type-arg]
) -> httpx.MockTransport:
    """Return a MockTransport that records each request and replies with the given status/body."""

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            status_code=status_code,
            content=json.dumps(response_body).encode(),
            headers={"Content-Type": "application/json"},
        )

    return httpx.MockTransport(handler)


def _patch_async_client(monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport) -> None:
    """Patch httpx.AsyncClient so that every instantiation receives the mock transport."""
    original_cls = httpx.AsyncClient

    def factory(*args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs["transport"] = transport
        return original_cls(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


@pytest.mark.anyio
async def test_send_posts_to_correct_url_with_form_encoded_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST goes to Twilio Messages.json URL with form-encoded body and correct return value."""
    captured: list[httpx.Request] = []
    transport = _make_mock_transport(captured, 201, {"sid": "SM-abc-123"})
    _patch_async_client(monkeypatch, transport)

    provider = TwilioSMSProvider("AC123", "secret-token", "+15550001111")
    result = await provider.send(recipient="+15551234567", subject="", body="hello")

    assert result == "SM-abc-123"
    assert len(captured) == 1
    req = captured[0]

    # Method and URL
    assert req.method == "POST"
    assert str(req.url) == "https://api.twilio.com/2010-04-01/Accounts/AC123/Messages.json"

    # Content-Type must be form-encoded
    content_type = req.headers.get("content-type", "")
    assert content_type.startswith("application/x-www-form-urlencoded")

    # Parse form body and flatten single-element lists
    raw_form = req.content.decode()
    parsed = urllib.parse.parse_qs(raw_form)
    flat = {k: v[0] for k, v in parsed.items()}
    assert flat == {"From": "+15550001111", "To": "+15551234567", "Body": "hello"}


@pytest.mark.anyio
async def test_send_uses_basic_auth_with_account_sid_and_auth_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Basic Auth header encodes account_sid as username and auth_token as password."""
    captured: list[httpx.Request] = []
    transport = _make_mock_transport(captured, 201, {"sid": "SM-xyz"})
    _patch_async_client(monkeypatch, transport)

    provider = TwilioSMSProvider("AC123", "secret-token", "+15550001111")
    await provider.send(recipient="+15551234567", subject="", body="hello")

    req = captured[0]
    auth_header = req.headers.get("authorization", "")
    assert auth_header.startswith("Basic ")

    decoded = base64.b64decode(auth_header.removeprefix("Basic ")).decode()
    assert decoded == "AC123:secret-token"


@pytest.mark.anyio
async def test_send_returns_empty_string_when_sid_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """send() returns '' when the response JSON has no sid key."""
    captured: list[httpx.Request] = []
    transport = _make_mock_transport(captured, 201, {})
    _patch_async_client(monkeypatch, transport)

    provider = TwilioSMSProvider("AC123", "secret-token", "+15550001111")
    result = await provider.send(recipient="+15551234567", subject="", body="hello")

    assert result == ""


@pytest.mark.anyio
async def test_send_raises_on_4xx_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """send() lets httpx.HTTPStatusError propagate on 4xx responses."""
    captured: list[httpx.Request] = []
    error_body = {
        "code": 21211,
        "message": "Invalid 'To' Phone Number",
        "status": 400,
    }
    transport = _make_mock_transport(captured, 400, error_body)
    _patch_async_client(monkeypatch, transport)

    provider = TwilioSMSProvider("AC123", "secret-token", "+15550001111")
    with pytest.raises(httpx.HTTPStatusError):
        await provider.send(recipient="+15551234567", subject="", body="hello")


@pytest.mark.anyio
async def test_send_ignores_subject_and_html_body_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Form body contains only From, To, Body — no subject or html_body fields."""
    captured: list[httpx.Request] = []
    transport = _make_mock_transport(captured, 201, {"sid": "SM-1"})
    _patch_async_client(monkeypatch, transport)

    provider = TwilioSMSProvider("AC123", "secret-token", "+15550001111")
    await provider.send(
        recipient="+15551234567",
        subject="ignored subject",
        body="hi",
        html_body="<p>ignored</p>",
    )

    req = captured[0]
    raw_form = req.content.decode()
    parsed = urllib.parse.parse_qs(raw_form)
    keys = set(parsed.keys())
    assert keys == {"From", "To", "Body"}


def test_channel_attribute_and_protocol_conformance() -> None:
    """TwilioSMSProvider.channel is sms and instance satisfies NotificationProvider."""
    provider = TwilioSMSProvider("AC123", "secret-token", "+15550001111")
    assert provider.channel == NotificationChannel.sms
    assert isinstance(provider, NotificationProvider)
