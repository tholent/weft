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

"""Log-safe helpers to prevent log injection from user-controlled data.

Use these functions whenever logging values that come from external input
(phone numbers, message bodies, form fields, etc.) to prevent CRLF injection
and control-character injection into log aggregation systems.
"""

import hashlib


def sanitize_for_log(value: str, max_len: int = 64) -> str:
    """Strip non-printable and CRLF characters then truncate to *max_len*."""
    cleaned = "".join(c for c in value if c.isprintable() and c not in "\r\n")
    return cleaned[:max_len]


def hash_for_log(value: str, length: int = 8) -> str:
    """Return a short SHA-256 hex digest of *value* for log correlation.

    Using a hash instead of the raw value avoids logging PII (phone numbers,
    email addresses) while still allowing log correlation by value.
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]
