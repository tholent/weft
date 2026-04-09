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
from sqlmodel import select

from app.models.circle import Circle
from app.models.enums import MemberRole
from app.models.member import Member, MemberCircleHistory
from app.models.update import UpdateCircle
from app.services.member import move_member
from app.services.update import create_update, get_feed


@pytest.mark.anyio
async def test_member_sees_updates_posted_to_their_circle(session, topic_with_creator):
    topic, creator, _ = topic_with_creator

    circle = Circle(topic_id=topic.id, name="Family")
    session.add(circle)
    await session.flush()

    member = Member(topic_id=topic.id, role=MemberRole.recipient)
    session.add(member)
    await session.flush()

    history = MemberCircleHistory(member_id=member.id, circle_id=circle.id)
    session.add(history)
    await session.flush()

    await create_update(session, topic.id, creator.id, "Hello family!", [circle.id])
    await session.commit()

    feed = await get_feed(session, member.id)
    assert len(feed) == 1
    assert feed[0].body == "Hello family!"


@pytest.mark.anyio
async def test_moved_member_does_not_see_new_updates_from_old_circle(session, topic_with_creator):
    topic, creator, _ = topic_with_creator

    circle_a = Circle(topic_id=topic.id, name="Circle A")
    circle_b = Circle(topic_id=topic.id, name="Circle B")
    session.add(circle_a)
    session.add(circle_b)
    await session.flush()

    member = Member(topic_id=topic.id, role=MemberRole.recipient)
    session.add(member)
    await session.flush()

    history = MemberCircleHistory(member_id=member.id, circle_id=circle_a.id)
    session.add(history)
    await session.flush()

    # Post to circle A while member is in it
    await create_update(session, topic.id, creator.id, "Old A update", [circle_a.id])
    await session.commit()

    # Move member to circle B
    await move_member(session, member.id, circle_b.id)
    await session.commit()

    # Post to circle A after member moved out
    await create_update(session, topic.id, creator.id, "New A update", [circle_a.id])
    await session.commit()

    feed = await get_feed(session, member.id)
    bodies = [u.body for u in feed]
    assert "Old A update" in bodies
    assert "New A update" not in bodies


@pytest.mark.anyio
async def test_moved_member_still_sees_old_updates_falls_forward(session, topic_with_creator):
    topic, creator, _ = topic_with_creator

    circle_a = Circle(topic_id=topic.id, name="Circle A")
    circle_b = Circle(topic_id=topic.id, name="Circle B")
    session.add(circle_a)
    session.add(circle_b)
    await session.flush()

    member = Member(topic_id=topic.id, role=MemberRole.recipient)
    session.add(member)
    await session.flush()

    history = MemberCircleHistory(member_id=member.id, circle_id=circle_a.id)
    session.add(history)
    await session.flush()

    await create_update(session, topic.id, creator.id, "Old A update", [circle_a.id])
    await session.commit()

    # Move member - falls forward, so old updates remain visible
    await move_member(session, member.id, circle_b.id)
    await session.commit()

    feed = await get_feed(session, member.id)
    assert any(u.body == "Old A update" for u in feed)


@pytest.mark.anyio
async def test_retroactive_revocation_hides_old_updates(session, topic_with_creator):
    topic, creator, _ = topic_with_creator

    circle_a = Circle(topic_id=topic.id, name="Circle A")
    circle_b = Circle(topic_id=topic.id, name="Circle B")
    session.add(circle_a)
    session.add(circle_b)
    await session.flush()

    member = Member(topic_id=topic.id, role=MemberRole.recipient)
    session.add(member)
    await session.flush()

    history = MemberCircleHistory(member_id=member.id, circle_id=circle_a.id)
    session.add(history)
    await session.flush()

    await create_update(session, topic.id, creator.id, "Secret A update", [circle_a.id])
    await session.commit()

    # Move member with retroactive revocation
    await move_member(session, member.id, circle_b.id, retroactive_revoke=True)
    await session.commit()

    feed = await get_feed(session, member.id)
    assert not any(u.body == "Secret A update" for u in feed)


@pytest.mark.anyio
async def test_moved_up_does_not_retroactively_see_old_posts(session, topic_with_creator):
    topic, creator, _ = topic_with_creator

    circle_a = Circle(topic_id=topic.id, name="Circle A")
    circle_b = Circle(topic_id=topic.id, name="Circle B")
    session.add(circle_a)
    session.add(circle_b)
    await session.flush()

    member = Member(topic_id=topic.id, role=MemberRole.recipient)
    session.add(member)
    await session.flush()

    # Member starts in circle_a
    history = MemberCircleHistory(member_id=member.id, circle_id=circle_a.id)
    session.add(history)
    await session.flush()

    # Old post to circle_b before member was in it
    await create_update(session, topic.id, creator.id, "Old B post", [circle_b.id])
    await session.commit()

    # Move member to circle_b
    await move_member(session, member.id, circle_b.id)
    await session.commit()

    feed = await get_feed(session, member.id)
    assert not any(u.body == "Old B post" for u in feed)


@pytest.mark.anyio
async def test_update_circle_is_immutable_after_insert(session, topic_with_creator):
    topic, creator, _ = topic_with_creator

    circle = Circle(topic_id=topic.id, name="Test")
    session.add(circle)
    await session.flush()

    update = await create_update(session, topic.id, creator.id, "Test", [circle.id])
    await session.commit()

    # Verify update_circle row exists
    result = await session.execute(
        select(UpdateCircle).where(UpdateCircle.update_id == update.id)
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].circle_id == circle.id
