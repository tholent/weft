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

import pytest

from app.models.circle import Circle
from app.models.enums import MemberRole, ModResponseScope
from app.models.member import Member, MemberCircleHistory
from app.services.reply import (
    create_mod_response,
    create_reply,
    get_mod_responses_for_reply,
    get_replies_for_update,
    relay_reply,
)
from app.services.update import create_update


@pytest.fixture
async def update_with_replies(session, topic_with_creator):
    """Create topic with circle, update, and replies."""
    topic, creator, _ = topic_with_creator

    circle = Circle(topic_id=topic.id, name="Family")
    session.add(circle)
    await session.flush()

    # Moderator
    mod = Member(topic_id=topic.id, role=MemberRole.moderator)
    session.add(mod)
    await session.flush()
    mod_history = MemberCircleHistory(member_id=mod.id, circle_id=circle.id)
    session.add(mod_history)

    # Two recipients
    r1 = Member(topic_id=topic.id, role=MemberRole.recipient)
    r2 = Member(topic_id=topic.id, role=MemberRole.recipient)
    session.add(r1)
    session.add(r2)
    await session.flush()

    for r in [r1, r2]:
        h = MemberCircleHistory(member_id=r.id, circle_id=circle.id)
        session.add(h)

    update = await create_update(session, topic.id, creator.id, "Update body", [circle.id])

    reply1 = await create_reply(session, update.id, r1.id, "Reply from r1")
    reply2 = await create_reply(session, update.id, r2.id, "Reply from r2")

    await session.commit()
    return {
        "topic": topic,
        "circle": circle,
        "creator": creator,
        "mod": mod,
        "r1": r1,
        "r2": r2,
        "update": update,
        "reply1": reply1,
        "reply2": reply2,
    }


@pytest.mark.anyio
async def test_recipient_sees_only_own_replies(session, update_with_replies):
    d = update_with_replies

    replies = await get_replies_for_update(session, d["update"].id, d["r1"])
    assert len(replies) == 1
    assert replies[0].body == "Reply from r1"


@pytest.mark.anyio
async def test_moderator_sees_all_replies(session, update_with_replies):
    d = update_with_replies

    replies = await get_replies_for_update(session, d["update"].id, d["mod"])
    assert len(replies) == 2


@pytest.mark.anyio
async def test_relay_creates_correct_rows(session, update_with_replies):
    d = update_with_replies

    relays = await relay_reply(session, d["reply1"].id, d["mod"].id, [d["circle"].id])
    await session.commit()

    assert len(relays) == 1
    assert relays[0].circle_id == d["circle"].id

    # r2 should now see r1's relayed reply
    replies = await get_replies_for_update(session, d["update"].id, d["r2"])
    bodies = [r.body for r in replies]
    assert "Reply from r1" in bodies
    assert "Reply from r2" in bodies


@pytest.mark.anyio
async def test_mod_response_sender_only_visible_to_author(session, update_with_replies):
    d = update_with_replies

    await create_mod_response(
        session, d["reply1"].id, d["mod"].id, "Private note", ModResponseScope.sender_only
    )
    await session.commit()

    # r1 (reply author) should see it
    responses = await get_mod_responses_for_reply(session, d["reply1"].id, d["r1"])
    assert len(responses) == 1

    # r2 should not see it
    responses = await get_mod_responses_for_reply(session, d["reply1"].id, d["r2"])
    assert len(responses) == 0

    # mod should see it
    responses = await get_mod_responses_for_reply(session, d["reply1"].id, d["mod"])
    assert len(responses) == 1


@pytest.mark.anyio
async def test_mod_response_sender_circle_visible_to_circle(session, update_with_replies):
    d = update_with_replies

    await create_mod_response(
        session, d["reply1"].id, d["mod"].id, "Circle note", ModResponseScope.sender_circle
    )
    await session.commit()

    # r2 shares the circle with r1, so should see it
    responses = await get_mod_responses_for_reply(session, d["reply1"].id, d["r2"])
    assert len(responses) == 1
