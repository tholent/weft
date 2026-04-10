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

"""FastAPI dependency for validating Twilio webhook signatures.

Twilio signs every webhook request with an HMAC-SHA1 of:

    URL + sorted(key + value for each POST parameter)

The result is base64-encoded and sent in the ``X-Twilio-Signature`` header.

When ``twilio_auth_token`` is empty (dev mode) validation is skipped with a
warning log so the local development environment still works without a live
Twilio account.
"""

import base64
import hashlib
import hmac
import logging

from fastapi import Depends, HTTPException, Request

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


def _compute_twilio_signature(auth_token: str, url: str, form_params: dict[str, str]) -> str:
    """Compute the expected Twilio signature for the given request parameters."""
    # Concatenate URL with sorted param key-value pairs (no separators)
    sorted_pairs = "".join(k + v for k, v in sorted(form_params.items()))
    s = url + sorted_pairs
    mac = hmac.new(auth_token.encode("utf-8"), s.encode("utf-8"), hashlib.sha1)
    return base64.b64encode(mac.digest()).decode("utf-8")


async def verify_twilio_signature(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    """Dependency that validates the Twilio webhook signature.

    Raises HTTP 403 if the signature is missing or invalid.
    Skips validation with a warning if ``twilio_auth_token`` is empty.
    """
    auth_token = settings.twilio_auth_token

    if not auth_token:
        logger.warning(
            "twilio_auth_token is not configured — skipping Twilio signature validation. "
            "Set TWILIO_AUTH_TOKEN in production."
        )
        return

    signature_header = request.headers.get("X-Twilio-Signature")
    if not signature_header:
        raise HTTPException(status_code=403, detail="Missing X-Twilio-Signature header")

    # Build the canonical URL: use settings.base_url as the scheme+host, keep the path+query
    # intact so it matches what Twilio signed.
    base_url = settings.base_url.rstrip("/")
    path = request.url.path
    query = request.url.query
    canonical_url = base_url + path + ("?" + query if query else "")

    # Read form body — await parse if not yet consumed
    form_data = await request.form()
    params: dict[str, str] = {k: str(v) for k, v in form_data.multi_items()}

    expected = _compute_twilio_signature(auth_token, canonical_url, params)

    if not hmac.compare_digest(expected, signature_header):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
