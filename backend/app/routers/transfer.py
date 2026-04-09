import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.session import get_session
from app.deps import require_admin, require_creator
from app.models.enums import TransferStatus
from app.models.member import Member
from app.models.transfer import CreatorTransfer
from app.schemas.transfer import TransferResponse
from app.services.transfer import cancel_transfer, request_transfer

router = APIRouter(prefix="/topics/{topic_id}/transfer", tags=["transfer"])


@router.post("", response_model=TransferResponse)
async def request_transfer_endpoint(
    topic_id: uuid.UUID,
    member: Member = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Request a creator transfer. Admin only."""
    try:
        transfer = await request_transfer(session, topic_id, member.id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return TransferResponse(
        id=transfer.id,
        status=transfer.status,
        deadline=transfer.deadline,
        created_at=transfer.created_at,
    )


@router.get("", response_model=TransferResponse | None)
async def get_transfer_status_endpoint(
    topic_id: uuid.UUID,
    member: Member = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Get current transfer status. Admin+ only."""
    result = await session.execute(
        select(CreatorTransfer).where(
            CreatorTransfer.topic_id == topic_id,
            CreatorTransfer.status == TransferStatus.pending,
        )
    )
    transfer = result.scalar_one_or_none()
    if transfer is None:
        return None
    return TransferResponse(
        id=transfer.id,
        status=transfer.status,
        deadline=transfer.deadline,
        created_at=transfer.created_at,
    )


@router.post("/cancel")
async def cancel_transfer_endpoint(
    topic_id: uuid.UUID,
    member: Member = Depends(require_creator),
    session: AsyncSession = Depends(get_session),
):
    """Cancel a pending transfer. Creator only."""
    await cancel_transfer(session, topic_id)
    return {"detail": "Transfer cancelled"}
