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

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.deps import SessionDep, TopicAdminDep, TopicOwnerDep
from app.models.enums import TransferStatus
from app.models.transfer import CreatorTransfer
from app.schemas.transfer import DirectTransferRequest, TransferResponse
from app.services.transfer import cancel_transfer, execute_direct_transfer, request_transfer

router = APIRouter(prefix="/topics/{topic_id}/transfer", tags=["transfer"])


@router.post("", response_model=TransferResponse)
async def request_transfer_endpoint(
    topic_id: uuid.UUID,
    member: TopicAdminDep,
    session: SessionDep,
):
    """Request a dead-man's-switch transfer. Admin only."""
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
    member: TopicAdminDep,
    session: SessionDep,
):
    """Get current pending transfer status. Admin+ only."""
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
    member: TopicOwnerDep,
    session: SessionDep,
):
    """Cancel a pending transfer. Owner only."""
    await cancel_transfer(session, topic_id)
    return {"detail": "Transfer cancelled"}


@router.post("/direct", response_model=TransferResponse)
async def direct_transfer_endpoint(
    topic_id: uuid.UUID,
    payload: DirectTransferRequest,
    member: TopicOwnerDep,
    session: SessionDep,
):
    """Immediately pass ownership to any member. Owner only."""
    try:
        transfer = await execute_direct_transfer(
            session, topic_id, payload.target_member_id, member.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return TransferResponse(
        id=transfer.id,
        status=transfer.status,
        deadline=transfer.deadline,
        created_at=transfer.created_at,
    )
