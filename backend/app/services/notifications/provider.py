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

from typing import Protocol, runtime_checkable

from app.models.enums import NotificationChannel


@runtime_checkable
class NotificationProvider(Protocol):
    """Protocol that all notification providers must implement."""

    channel: NotificationChannel

    async def send(
        self,
        *,
        recipient: str,
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> str:
        """Send a notification to the recipient.

        Args:
            recipient: The destination address (email address or phone number).
            subject: The subject line (used for email; may be ignored for SMS).
            body: The plain-text body of the message.
            html_body: Optional HTML body (used for email only).

        Returns:
            A provider-specific message ID string for tracking.
        """
        ...
