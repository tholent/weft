from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.session import get_session
from app.deps import get_current_member
from app.models.member import Member
from app.schemas.auth import AuthResponse, MagicLinkVerify
from app.services.auth import generate_token, hash_token, revoke_token, verify_magic_link

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/verify", response_model=AuthResponse)
async def verify_magic_link_endpoint(
    payload: MagicLinkVerify,
    session: AsyncSession = Depends(get_session),
):
    """Verify a magic link and issue a fresh bearer token."""
    try:
        data = verify_magic_link(payload.token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    member_id = data["member_id"]

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
    member: Member = Depends(get_current_member),
    session: AsyncSession = Depends(get_session),
):
    """Revoke the current bearer token."""
    auth_header = request.headers.get("Authorization", "")
    raw_token = auth_header.removeprefix("Bearer ").strip()
    token_hash = hash_token(raw_token)
    await revoke_token(session, token_hash)
    return {"detail": "Token revoked"}
