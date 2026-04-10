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

_MAILGUN_API_BASE = "https://api.mailgun.net/v3"


class MailgunEmailProvider:
    """Email notification provider backed by the Mailgun API."""

    channel: NotificationChannel = NotificationChannel.email

    def __init__(
        self,
        api_key: str,
        domain: str,
        from_address: str = "Weft <noreply@weft.app>",
    ) -> None:
        self.api_key = api_key
        self.domain = domain
        self.from_address = from_address

    async def send(
        self,
        *,
        recipient: str,
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> str:
        """Send an email via Mailgun. Returns the provider message ID."""
        data: dict[str, str] = {
            "from": self.from_address,
            "to": recipient,
            "subject": subject,
            "text": body,
        }
        if html_body is not None:
            data["html"] = html_body

        url = f"{_MAILGUN_API_BASE}/{self.domain}/messages"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                auth=("api", self.api_key),
                data=data,
            )
            response.raise_for_status()
            result = response.json()
            return str(result.get("id", ""))
