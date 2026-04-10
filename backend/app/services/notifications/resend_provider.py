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

import asyncio
import logging

from app.models.enums import NotificationChannel

logger = logging.getLogger(__name__)


class ResendEmailProvider:
    """Email notification provider backed by the Resend API."""

    channel: NotificationChannel = NotificationChannel.email

    def __init__(self, api_key: str, from_address: str = "Weft <noreply@weft.app>") -> None:
        self.api_key = api_key
        self.from_address = from_address

    async def send(
        self,
        *,
        recipient: str,
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> str:
        """Send an email via Resend. Returns the provider message ID."""
        import resend

        resend.api_key = self.api_key

        payload: dict[str, object] = {
            "from": self.from_address,
            "to": [recipient],
            "subject": subject,
            "text": body,
        }
        if html_body is not None:
            payload["html"] = html_body

        def _send() -> object:
            return resend.Emails.send(payload)

        result = await asyncio.to_thread(_send)
        # Resend returns a dict-like object with an "id" key
        if isinstance(result, dict):
            return str(result.get("id", ""))
        return str(getattr(result, "id", ""))
