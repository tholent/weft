import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.deps import require_topic_admin, require_topic_member
from app.models.enums import MemberRole
from app.models.member import Member, MemberCircleHistory
from app.schemas.circle import CircleCreate, CircleResponse, CircleUpdate
from app.services.circle import create_circle, delete_circle, list_circles, rename_circle

router = APIRouter(prefix="/topics/{topic_id}/circles", tags=["circles"])


@router.post("", response_model=CircleResponse)
async def create_circle_endpoint(
    topic_id: uuid.UUID,
    payload: CircleCreate,
    member: Member = Depends(require_topic_admin),
    session: AsyncSession = Depends(get_session),
):
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
    member: Member = Depends(require_topic_member),
    session: AsyncSession = Depends(get_session),
):
    """List circles. Admin+ sees all; recipients see only their own circle."""
    if member.role in (MemberRole.creator, MemberRole.admin, MemberRole.moderator):
        circles = await list_circles(session, topic_id)
    else:
        # Recipient: only their active circle
        from sqlmodel import select

        from app.models.circle import Circle

        result = await session.execute(
            select(MemberCircleHistory).where(
                MemberCircleHistory.member_id == member.id,
                MemberCircleHistory.revoked_at.is_(None),  # type: ignore[union-attr]
            )
        )
        active = result.scalars().first()
        if active:
            result = await session.execute(select(Circle).where(Circle.id == active.circle_id))
            circle = result.scalar_one_or_none()
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
    member: Member = Depends(require_topic_admin),
    session: AsyncSession = Depends(get_session),
):
    circle = await rename_circle(
        session, circle_id, payload.name, payload.scoped_title, payload.clear_scoped_title
    )
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
    member: Member = Depends(require_topic_admin),
    session: AsyncSession = Depends(get_session),
):
    try:
        await delete_circle(session, circle_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"detail": "Circle deleted"}
