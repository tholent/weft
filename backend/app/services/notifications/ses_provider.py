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


class SESEmailProvider:
    """Email notification provider backed by Amazon SES (via boto3)."""

    channel: NotificationChannel = NotificationChannel.email

    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        aws_region: str,
        from_address: str = "Weft <noreply@weft.app>",
    ) -> None:
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region = aws_region
        self.from_address = from_address

    async def send(
        self,
        *,
        recipient: str,
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> str:
        """Send an email via Amazon SES. Returns the provider message ID."""
        return await asyncio.to_thread(self._send_sync, recipient, subject, body, html_body)

    def _send_sync(
        self,
        recipient: str,
        subject: str,
        body: str,
        html_body: str | None,
    ) -> str:
        import boto3  # type: ignore[import-untyped]

        client = boto3.client(
            "ses",
            region_name=self.aws_region,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
        )

        body_content: dict[str, object] = {
            "Text": {"Data": body, "Charset": "UTF-8"},
        }
        if html_body is not None:
            body_content["Html"] = {"Data": html_body, "Charset": "UTF-8"}

        response = client.send_email(
            Source=self.from_address,
            Destination={"ToAddresses": [recipient]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": body_content,
            },
        )
        return str(response.get("MessageId", ""))
