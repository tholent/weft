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

"""Unit tests for VonageSMSProvider — exercises the exact wire format without
standing up the full dispatch pipeline."""

import json

import httpx
import pytest

from app.models.enums import NotificationChannel
from app.services.notifications.provider import NotificationProvider
from app.services.notifications.vonage_provider import VonageSMSProvider


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
async def test_send_posts_expected_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST goes to the Vonage Messages API URL with correct JSON body and Basic Auth."""
    captured: list[httpx.Request] = []
    transport = _make_mock_transport(captured, 202, {"message_uuid": "abc-123"})
    _patch_async_client(monkeypatch, transport)

    provider = VonageSMSProvider("my-key", "my-secret", "Weft")
    result = await provider.send(recipient="+15551234567", subject="", body="hello")

    assert result == "abc-123"
    assert len(captured) == 1
    req = captured[0]

    # Method and URL
    assert req.method == "POST"
    assert str(req.url) == "https://api.nexmo.com/v1/messages"

    # Basic Auth header
    auth_header = req.headers.get("authorization", "")
    assert auth_header.startswith("Basic ")

    import base64

    decoded = base64.b64decode(auth_header.removeprefix("Basic ")).decode()
    assert decoded == "my-key:my-secret"

    # JSON body
    body = json.loads(req.content)
    assert body == {
        "channel": "sms",
        "message_type": "text",
        "to": "+15551234567",
        "from": "Weft",
        "text": "hello",
    }


@pytest.mark.anyio
async def test_send_returns_empty_string_when_message_uuid_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """send() returns '' when the response JSON has no message_uuid key."""
    captured: list[httpx.Request] = []
    transport = _make_mock_transport(captured, 202, {})
    _patch_async_client(monkeypatch, transport)

    provider = VonageSMSProvider("k", "s", "Weft")
    result = await provider.send(recipient="+15551234567", subject="", body="hello")

    assert result == ""


@pytest.mark.anyio
async def test_send_raises_on_4xx_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """send() lets httpx.HTTPStatusError propagate on 4xx responses."""
    captured: list[httpx.Request] = []
    problem = {
        "type": "https://developer.vonage.com/api-errors#invalid-params",
        "title": "Invalid params",
        "detail": "The request body is invalid",
        "instance": "bf0ca0bf-test-4567-bded-3b19f60ebc8",
    }
    transport = _make_mock_transport(captured, 422, problem)
    _patch_async_client(monkeypatch, transport)

    provider = VonageSMSProvider("k", "s", "Weft")
    with pytest.raises(httpx.HTTPStatusError):
        await provider.send(recipient="+15551234567", subject="", body="hello")


def test_channel_attribute_and_protocol_conformance() -> None:
    """VonageSMSProvider.channel is sms and instance satisfies NotificationProvider."""
    provider = VonageSMSProvider("k", "s", "Weft")
    assert provider.channel == NotificationChannel.sms
    assert isinstance(provider, NotificationProvider)
