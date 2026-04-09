import pytest
from sqlmodel import select

from app.models.enums import MemberRole
from app.models.member import Member
from app.models.topic import Topic
from app.services.purge import purge_emails


@pytest.mark.anyio
async def test_purge_sets_emails_to_none(session, topic_with_creator):
    topic, creator, _ = topic_with_creator
    topic_id = topic.id

    # Add another member with email
    m = Member(topic_id=topic_id, role=MemberRole.recipient, email="test@test.com")
    session.add(m)
    await session.commit()

    await purge_emails(session, topic_id)
    await session.commit()

    # Re-fetch to see changes
    session.expire_all()
    result = await session.execute(select(Member).where(Member.topic_id == topic_id))
    for member in result.scalars().all():
        assert member.email is None
        assert member.email_purged_at is not None


@pytest.mark.anyio
async def test_purge_only_affects_target_topic(session, topic_with_creator):
    topic, creator, _ = topic_with_creator

    # Create another topic with a member
    other_topic = Topic(default_title="Other")
    session.add(other_topic)
    await session.flush()
    other_member = Member(
        topic_id=other_topic.id, role=MemberRole.recipient, email="other@test.com"
    )
    session.add(other_member)
    await session.commit()

    await purge_emails(session, topic.id)
    await session.commit()

    await session.refresh(other_member)
    assert other_member.email == "other@test.com"
    assert other_member.email_purged_at is None


@pytest.mark.anyio
async def test_close_topic_triggers_purge(session, topic_with_creator):
    """Closing a topic via the service layer triggers email purge."""
    topic, creator, _ = topic_with_creator
    topic_id = topic.id

    from app.services.topic import close_topic

    await close_topic(session, topic_id)
    await session.commit()

    session.expire_all()
    result = await session.execute(select(Member).where(Member.topic_id == topic_id))
    for member in result.scalars().all():
        assert member.email is None
