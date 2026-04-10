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

import logging

import httpx

from app.models.enums import NotificationChannel

logger = logging.getLogger(__name__)

_VONAGE_API_URL = "https://api.nexmo.com/v1/messages"


class VonageSMSProvider:
    """SMS notification provider backed by the Vonage Messages API."""

    channel: NotificationChannel = NotificationChannel.sms

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        from_sender: str,
    ) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.from_sender = from_sender

    async def send(
        self,
        *,
        recipient: str,
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> str:
        """Send an SMS via Vonage Messages API. Subject and html_body are ignored.
        Returns the provider message UUID."""
        payload = {
            "channel": "sms",
            "message_type": "text",
            "to": recipient,
            "from": self.from_sender,
            "text": body,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                _VONAGE_API_URL,
                json=payload,
                auth=(self.api_key, self.api_secret),
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            result = response.json()
            return str(result.get("message_uuid", ""))
