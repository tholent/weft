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

from fastapi import APIRouter, Request
from sqlmodel import col, select

from app.config import get_settings
from app.deps import SessionDep, TopicMemberDep, TopicOwnerDep
from app.models.circle import Circle
from app.models.enums import MemberRole
from app.models.member import MemberCircleHistory
from app.rate_limit import limiter
from app.schemas.topic import TopicCreate, TopicCreateResponse, TopicResponse
from app.services.email import send_invite_email
from app.services.topic import close_topic, create_topic, get_topic

router = APIRouter(prefix="/topics", tags=["topics"])


def _topic_creation_rate_limit() -> str:
    return get_settings().topic_creation_rate_limit


@router.post("", response_model=TopicCreateResponse)
@limiter.limit(_topic_creation_rate_limit)
async def create_topic_endpoint(
    request: Request,
    payload: TopicCreate,
    session: SessionDep,
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
    member: TopicMemberDep,
    session: SessionDep,
):
    """Get topic info. Returns scoped title based on viewer's circle."""
    topic = await get_topic(session, topic_id)

    scoped_title = None
    if member.role == MemberRole.recipient:
        # Get member's active circle and its scoped title
        history_result = await session.execute(
            select(MemberCircleHistory).where(
                MemberCircleHistory.member_id == member.id,
                col(MemberCircleHistory.revoked_at).is_(None),
            )
        )
        active_history = history_result.scalars().first()
        if active_history:
            circle_result = await session.execute(
                select(Circle).where(Circle.id == active_history.circle_id)
            )
            circle = circle_result.scalar_one_or_none()
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
    member: TopicOwnerDep,
    session: SessionDep,
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
