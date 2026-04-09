import pytest
from sqlmodel import select

from app.models.enums import TopicStatus
from app.models.member import Member


@pytest.mark.anyio
async def test_create_topic_returns_magic_link(client):
    resp = await client.post(
        "/topics",
        json={"default_title": "Family Update"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["token"]
    assert data["magic_link"]
    assert data["topic"]["default_title"] == "Family Update"
    assert data["topic"]["status"] == "active"


@pytest.mark.anyio
async def test_close_topic_purges_emails(client, session, topic_with_creator):
    topic, creator, raw_token = topic_with_creator

    resp = await client.post(
        f"/topics/{topic.id}/close",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"

    # Check emails are purged (expire cache since client used different session)
    topic_id = topic.id
    session.expire_all()
    result = await session.execute(select(Member).where(Member.topic_id == topic_id))
    for member in result.scalars().all():
        assert member.email is None
        assert member.email_purged_at is not None


@pytest.mark.anyio
async def test_closed_topic_returns_403(client, session, topic_with_creator):
    topic, creator, raw_token = topic_with_creator

    # Close the topic
    topic.status = TopicStatus.closed
    session.add(topic)
    await session.commit()

    resp = await client.get(
        f"/topics/{topic.id}",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_scoped_title_for_recipient(client, session, circle_with_members):
    circle, members, tokens = circle_with_members

    # Set a scoped title
    circle.scoped_title = "Grandma is in the hospital"
    session.add(circle)
    await session.commit()

    topic_id = circle.topic_id
    resp = await client.get(
        f"/topics/{topic_id}",
        headers={"Authorization": f"Bearer {tokens[0]}"},
    )
    assert resp.status_code == 200
    assert resp.json()["scoped_title"] == "Grandma is in the hospital"
