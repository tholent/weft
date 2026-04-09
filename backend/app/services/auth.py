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

import hashlib
import secrets
from datetime import UTC, datetime

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import get_settings
from app.models.token import Token


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def generate_token(session: AsyncSession, member_id) -> str:
    raw = secrets.token_urlsafe(32)
    token_row = Token(member_id=member_id, token_hash=hash_token(raw))
    session.add(token_row)
    await session.flush()
    return raw


def _get_serializer() -> URLSafeTimedSerializer:
    settings = get_settings()
    return URLSafeTimedSerializer(settings.secret_key)


def create_magic_link(member_id: str) -> str:
    """Create a magic link containing only member_id and a nonce (no bearer token)."""
    settings = get_settings()
    s = _get_serializer()
    nonce = secrets.token_urlsafe(16)
    signed = s.dumps({"member_id": str(member_id), "nonce": nonce})
    return f"{settings.base_url}/auth?t={signed}"


def verify_magic_link(signed_token: str, max_age: int = 86400) -> dict:
    """Verify a signed magic link token. Returns {"member_id": ...}."""
    s = _get_serializer()
    try:
        data = s.loads(signed_token, max_age=max_age)
    except SignatureExpired:
        raise ValueError("Magic link has expired")
    except BadSignature:
        raise ValueError("Invalid magic link")
    return data


async def revoke_token(session: AsyncSession, token_hash: str) -> None:
    result = await session.execute(select(Token).where(Token.token_hash == token_hash))
    token_row = result.scalar_one_or_none()
    if token_row is not None:
        token_row.revoked_at = datetime.now(UTC)
        session.add(token_row)
