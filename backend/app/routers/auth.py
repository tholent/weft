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

import uuid

from fastapi import APIRouter, HTTPException, Request
from sqlmodel import select

from app.deps import CurrentMemberDep, SessionDep
from app.models.member import Member
from app.schemas.auth import AuthResponse, MagicLinkVerify
from app.services.auth import generate_token, hash_token, revoke_token, verify_magic_link

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/verify", response_model=AuthResponse)
async def verify_magic_link_endpoint(
    payload: MagicLinkVerify,
    session: SessionDep,
):
    """Verify a magic link and issue a fresh bearer token."""
    try:
        data = verify_magic_link(payload.token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    member_id = uuid.UUID(data["member_id"])

    result = await session.execute(select(Member).where(Member.id == member_id))
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=401, detail="Member not found")

    # Generate a fresh bearer token on each magic link verification
    raw_token = await generate_token(session, member.id)

    return AuthResponse(
        token=raw_token,
        member_id=member.id,
        role=member.role,
        topic_id=member.topic_id,
    )


@router.post("/revoke")
async def revoke_current_token(
    request: Request,
    member: CurrentMemberDep,
    session: SessionDep,
):
    """Revoke the current bearer token."""
    auth_header = request.headers.get("Authorization", "")
    raw_token = auth_header.removeprefix("Bearer ").strip()
    token_hash = hash_token(raw_token)
    await revoke_token(session, token_hash)
    return {"detail": "Token revoked"}
