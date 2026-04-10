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


class SNSSMSProvider:
    """SMS notification provider backed by Amazon SNS (via boto3)."""

    channel: NotificationChannel = NotificationChannel.sms

    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        aws_region: str,
        sender_id: str = "Weft",
    ) -> None:
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region = aws_region
        self.sender_id = sender_id

    async def send(
        self,
        *,
        recipient: str,
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> str:
        """Send an SMS via Amazon SNS. Subject and html_body are ignored.
        Returns the provider message ID."""
        return await asyncio.to_thread(self._send_sync, recipient, body)

    def _send_sync(self, recipient: str, body: str) -> str:
        import boto3  # type: ignore[import-untyped]

        client = boto3.client(
            "sns",
            region_name=self.aws_region,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
        )

        response = client.publish(
            PhoneNumber=recipient,
            Message=body,
            MessageAttributes={
                "AWS.SNS.SMS.SenderID": {
                    "DataType": "String",
                    "StringValue": self.sender_id,
                },
                "AWS.SNS.SMS.SMSType": {
                    "DataType": "String",
                    "StringValue": "Transactional",
                },
            },
        )
        return str(response.get("MessageId", ""))
