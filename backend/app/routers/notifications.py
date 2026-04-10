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

"""Notification preference endpoints."""

import uuid

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.deps import SessionDep, TopicMemberDep
from app.models.enums import MemberRole
from app.models.member import Member as MemberModel
from app.schemas.notification import (
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
)
from app.services.notifications.preferences import (
    get_preferences,
    update_preference,
)

router = APIRouter(
    prefix="/topics/{topic_id}/members/{member_id}/notifications",
    tags=["notifications"],
)


@router.get("")
async def list_preferences(
    topic_id: uuid.UUID,
    member_id: uuid.UUID,
    current_member: TopicMemberDep,
    session: SessionDep,
) -> list[NotificationPreferenceResponse]:
    """List notification preferences for a member.

    A member may only retrieve their own preferences.  Admins and owners
    may retrieve preferences for any member in their topic.
    """
    # Authorisation: self or admin+
    if current_member.id != member_id:
        if current_member.role not in (MemberRole.owner, MemberRole.admin):
            raise HTTPException(status_code=403, detail="Access denied")
        # Verify the target member belongs to this topic
        result = await session.execute(
            select(MemberModel).where(
                MemberModel.id == member_id,
                MemberModel.topic_id == topic_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Member not found")

    prefs = await get_preferences(session, member_id)
    return [
        NotificationPreferenceResponse(
            id=p.id,
            member_id=p.member_id,
            channel=p.channel,
            trigger=p.trigger,
            delivery_mode=p.delivery_mode,
        )
        for p in prefs
    ]


@router.put("")
async def set_preference(
    topic_id: uuid.UUID,
    member_id: uuid.UUID,
    payload: NotificationPreferenceUpdate,
    current_member: TopicMemberDep,
    session: SessionDep,
) -> NotificationPreferenceResponse:
    """Create or update a single notification preference.

    Members may only update their own preferences.
    """
    if current_member.id != member_id:
        raise HTTPException(status_code=403, detail="Cannot modify another member's preferences")

    try:
        pref = await update_preference(
            session,
            member_id=member_id,
            trigger=payload.trigger,
            channel=payload.channel,
            delivery_mode=payload.delivery_mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return NotificationPreferenceResponse(
        id=pref.id,
        member_id=pref.member_id,
        channel=pref.channel,
        trigger=pref.trigger,
        delivery_mode=pref.delivery_mode,
    )
