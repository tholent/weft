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

_TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"


class TwilioSMSProvider:
    """SMS notification provider backed by the Twilio API."""

    channel: NotificationChannel = NotificationChannel.sms

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
    ) -> None:
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number

    async def send(
        self,
        *,
        recipient: str,
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> str:
        """Send an SMS via Twilio. Subject is ignored; html_body is ignored.
        Returns the provider message SID."""
        url = f"{_TWILIO_API_BASE}/Accounts/{self.account_sid}/Messages.json"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                auth=(self.account_sid, self.auth_token),
                data={
                    "From": self.from_number,
                    "To": recipient,
                    "Body": body,
                },
            )
            response.raise_for_status()
            result = response.json()
            return str(result.get("sid", ""))
