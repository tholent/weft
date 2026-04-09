import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.deps import require_topic_creator, require_topic_member
from app.models.enums import MemberRole
from app.models.member import Member, MemberCircleHistory
from app.rate_limit import limiter
from app.schemas.topic import TopicCreate, TopicCreateResponse, TopicResponse
from app.services.email import send_invite_email
from app.services.topic import close_topic, create_topic, get_topic

router = APIRouter(prefix="/topics", tags=["topics"])


@router.post("", response_model=TopicCreateResponse)
@limiter.limit("10/hour")
async def create_topic_endpoint(
    request: Request,
    payload: TopicCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new topic. No auth required."""
    topic, member, magic_link = await create_topic(
        session, payload.default_title, payload.creator_email
    )

    if payload.creator_email:
        await send_invite_email(payload.creator_email, payload.default_title, magic_link)

    return TopicCreateResponse(
        topic=TopicResponse(
            id=topic.id,
            default_title=topic.default_title,
            status=topic.status,
            created_at=topic.created_at,
        ),
        magic_link=magic_link,
    )


@router.get("/{topic_id}", response_model=TopicResponse)
async def get_topic_endpoint(
    topic_id: uuid.UUID,
    member: Member = Depends(require_topic_member),
    session: AsyncSession = Depends(get_session),
):
    """Get topic info. Returns scoped title based on viewer's circle."""
    topic = await get_topic(session, topic_id)

    scoped_title = None
    if member.role == MemberRole.recipient:
        # Get member's active circle and its scoped title
        from sqlmodel import select

        from app.models.circle import Circle

        result = await session.execute(
            select(MemberCircleHistory).where(
                MemberCircleHistory.member_id == member.id,
                MemberCircleHistory.revoked_at.is_(None),  # type: ignore[union-attr]
            )
        )
        active_history = result.scalars().first()
        if active_history:
            result = await session.execute(
                select(Circle).where(Circle.id == active_history.circle_id)
            )
            circle = result.scalar_one_or_none()
            if circle and circle.scoped_title:
                scoped_title = circle.scoped_title

    return TopicResponse(
        id=topic.id,
        default_title=topic.default_title,
        status=topic.status,
        created_at=topic.created_at,
        closed_at=topic.closed_at,
        scoped_title=scoped_title,
    )


@router.post("/{topic_id}/close", response_model=TopicResponse)
async def close_topic_endpoint(
    topic_id: uuid.UUID,
    member: Member = Depends(require_topic_creator),
    session: AsyncSession = Depends(get_session),
):
    """Close a topic. Creator only. Purges all emails."""
    topic = await close_topic(session, topic_id)
    return TopicResponse(
        id=topic.id,
        default_title=topic.default_title,
        status=topic.status,
        created_at=topic.created_at,
        closed_at=topic.closed_at,
    )
