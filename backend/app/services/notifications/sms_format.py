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

"""SMS message formatting utilities.

SMS character limits:
- Single SMS: 160 characters
- MMS / long SMS: 1600 characters (practical limit for content-heavy messages)

All formatters truncate the body with ellipsis to stay within the limit.
"""

_SMS_LIMIT = 160
_MMS_LIMIT = 1600


def _truncate(text: str, max_len: int) -> str:
    """Truncate *text* to *max_len* chars, appending '…' if truncated."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "\u2026"


def format_update_sms(
    topic_title: str,
    short_code: str,
    author_handle: str | None,
    body: str,
) -> str:
    """Format an update notification for SMS delivery.

    Example: "[Spring Break #A3F] Update from Jean: <body>"
    """
    author_str = author_handle or "moderator"
    prefix = f"[{topic_title} #{short_code}] Update from {author_str}: "
    available = _SMS_LIMIT - len(prefix)
    if available <= 0:
        return _truncate(prefix.rstrip(": "), _SMS_LIMIT)
    return prefix + _truncate(body, available)


def format_relay_sms(
    topic_title: str,
    short_code: str,
    author_identity: str,
    body: str,
) -> str:
    """Format a relayed reply notification for SMS delivery.

    Example: "[Spring Break #A3F] Reply from "Jean's coworker Mike": <body>"
    """
    prefix = f'[{topic_title} #{short_code}] Reply from "{author_identity}": '
    available = _SMS_LIMIT - len(prefix)
    if available <= 0:
        return _truncate(prefix.rstrip(": "), _SMS_LIMIT)
    return prefix + _truncate(body, available)


def format_invite_sms(topic_title: str, magic_link: str) -> str:
    """Format a member invite notification for SMS delivery.

    Example: "You've been invited to follow "Spring Break". View updates: <link>"
    """
    prefix = f'You\'ve been invited to follow "{topic_title}". View updates: '
    message = prefix + magic_link
    return _truncate(message, _MMS_LIMIT)


def format_digest_sms(
    topic_title: str,
    short_code: str,
    update_count: int,
    link: str,
) -> str:
    """Format a digest summary notification for SMS delivery.

    Example: "[Spring Break #A3F] 3 new updates. View: <link>"
    """
    noun = "update" if update_count == 1 else "updates"
    prefix = f"[{topic_title} #{short_code}] {update_count} new {noun}. View: "
    message = prefix + link
    return _truncate(message, _SMS_LIMIT)
