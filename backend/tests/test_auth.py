from datetime import UTC, datetime

import pytest
from sqlmodel import select

from app.models.enums import MemberRole, TransferStatus
from app.models.token import Token
from app.models.transfer import CreatorTransfer
from app.services.auth import hash_token


@pytest.mark.anyio
async def test_valid_token_resolves(client, topic_with_creator):
    topic, creator, raw_token = topic_with_creator
    resp = await client.get(
        f"/topics/{topic.id}",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == str(topic.id)


@pytest.mark.anyio
async def test_revoked_token_returns_401(client, session, topic_with_creator):
    topic, creator, raw_token = topic_with_creator

    # Revoke the token
    result = await session.execute(
        select(Token).where(Token.token_hash == hash_token(raw_token))
    )
    token_row = result.scalar_one()
    token_row.revoked_at = datetime.now(UTC)
    session.add(token_row)
    await session.commit()

    resp = await client.get(
        f"/topics/{topic.id}",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_invalid_token_returns_401(client):
    resp = await client.get(
        "/topics/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_creator_auth_cancels_pending_transfer(client, session, topic_with_creator):
    topic, creator, raw_token = topic_with_creator

    # Create an admin member
    from app.models.member import Member
    admin = Member(topic_id=topic.id, role=MemberRole.admin, email="admin@test.com")
    session.add(admin)
    await session.flush()

    # Create a pending transfer
    transfer = CreatorTransfer(
        topic_id=topic.id,
        requested_by_member_id=admin.id,
        deadline=datetime(2099, 1, 1, tzinfo=UTC),
    )
    session.add(transfer)
    await session.commit()

    # Creator authenticates
    resp = await client.get(
        f"/topics/{topic.id}",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert resp.status_code == 200

    # Transfer should be denied
    await session.refresh(transfer)
    assert transfer.status == TransferStatus.denied


@pytest.mark.anyio
async def test_token_last_used_at_updated(client, session, topic_with_creator):
    topic, creator, raw_token = topic_with_creator

    resp = await client.get(
        f"/topics/{topic.id}",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert resp.status_code == 200

    result = await session.execute(
        select(Token).where(Token.token_hash == hash_token(raw_token))
    )
    token_row = result.scalar_one()
    assert token_row.last_used_at is not None
