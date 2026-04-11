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
from sqlmodel import col, select

from app.deps import SessionDep, TopicAdminDep, TopicMemberDep
from app.models.circle import Circle
from app.models.enums import MemberRole
from app.models.member import MemberCircleHistory
from app.schemas.circle import CircleCreate, CircleResponse, CircleUpdate
from app.services.circle import create_circle, delete_circle, list_circles, rename_circle

router = APIRouter(prefix="/topics/{topic_id}/circles", tags=["circles"])


@router.post("", response_model=CircleResponse)
async def create_circle_endpoint(
    topic_id: uuid.UUID,
    payload: CircleCreate,
    member: TopicAdminDep,
    session: SessionDep,
) -> CircleResponse:
    circle = await create_circle(session, topic_id, payload.name, payload.scoped_title)
    return CircleResponse(
        id=circle.id,
        name=circle.name,
        scoped_title=circle.scoped_title,
        created_at=circle.created_at,
    )


@router.get("", response_model=list[CircleResponse])
async def list_circles_endpoint(
    topic_id: uuid.UUID,
    member: TopicMemberDep,
    session: SessionDep,
) -> list[CircleResponse]:
    """List circles. Admin+ sees all; recipients see only their own circle."""
    if member.role in (MemberRole.owner, MemberRole.admin, MemberRole.moderator):
        circles = await list_circles(session, topic_id)
    else:
        # Recipient: only their active circle
        history_result = await session.execute(
            select(MemberCircleHistory).where(
                MemberCircleHistory.member_id == member.id,
                col(MemberCircleHistory.revoked_at).is_(None),
            )
        )
        active = history_result.scalars().first()
        if active:
            circle_result = await session.execute(
                select(Circle).where(Circle.id == active.circle_id)
            )
            circle = circle_result.scalar_one_or_none()
            circles = [circle] if circle else []
        else:
            circles = []

    return [
        CircleResponse(
            id=c.id,
            name=c.name,
            scoped_title=c.scoped_title,
            created_at=c.created_at,
        )
        for c in circles
    ]


@router.patch("/{circle_id}", response_model=CircleResponse)
async def rename_circle_endpoint(
    topic_id: uuid.UUID,
    circle_id: uuid.UUID,
    payload: CircleUpdate,
    member: TopicAdminDep,
    session: SessionDep,
) -> CircleResponse:
    try:
        circle = await rename_circle(
            session,
            circle_id,
            topic_id,
            payload.name,
            payload.scoped_title,
            payload.clear_scoped_title,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return CircleResponse(
        id=circle.id,
        name=circle.name,
        scoped_title=circle.scoped_title,
        created_at=circle.created_at,
    )


@router.delete("/{circle_id}")
async def delete_circle_endpoint(
    topic_id: uuid.UUID,
    circle_id: uuid.UUID,
    member: TopicAdminDep,
    session: SessionDep,
) -> dict[str, str]:
    try:
        await delete_circle(session, circle_id, topic_id)
    except ValueError as e:
        err = str(e)
        if err == "Circle not found":
            raise HTTPException(status_code=404, detail=err)
        raise HTTPException(status_code=409, detail=err)
    return {"detail": "Circle deleted"}
