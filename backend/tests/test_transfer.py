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

from datetime import UTC, datetime, timedelta

import pytest

from app.models.enums import MemberRole, TransferStatus
from app.models.member import Member
from app.models.transfer import CreatorTransfer
from app.services.transfer import execute_transfer, request_transfer


@pytest.mark.anyio
async def test_admin_can_request_transfer(session, topic_with_creator):
    topic, creator, _ = topic_with_creator

    admin = Member(topic_id=topic.id, role=MemberRole.admin, email="admin@test.com")
    session.add(admin)
    await session.flush()
    await session.commit()

    transfer = await request_transfer(session, topic.id, admin.id)
    await session.commit()
    assert transfer.status == TransferStatus.pending


@pytest.mark.anyio
async def test_non_admin_cannot_request_transfer(session, topic_with_creator):
    topic, creator, _ = topic_with_creator

    recipient = Member(topic_id=topic.id, role=MemberRole.recipient)
    session.add(recipient)
    await session.flush()
    await session.commit()

    with pytest.raises(ValueError, match="Only admins"):
        await request_transfer(session, topic.id, recipient.id)


@pytest.mark.anyio
async def test_only_one_pending_transfer_per_topic(session, topic_with_creator):
    topic, creator, _ = topic_with_creator

    admin = Member(topic_id=topic.id, role=MemberRole.admin, email="admin@test.com")
    session.add(admin)
    await session.flush()
    await session.commit()

    await request_transfer(session, topic.id, admin.id)
    await session.commit()

    with pytest.raises(ValueError, match="already pending"):
        await request_transfer(session, topic.id, admin.id)


@pytest.mark.anyio
async def test_creator_auth_cancels_transfer(client, session, topic_with_creator):
    topic, creator, raw_token = topic_with_creator

    admin = Member(topic_id=topic.id, role=MemberRole.admin)
    session.add(admin)
    await session.flush()

    transfer = CreatorTransfer(
        topic_id=topic.id,
        requested_by_member_id=admin.id,
        deadline=datetime(2099, 1, 1, tzinfo=UTC),
    )
    session.add(transfer)
    await session.commit()

    # Creator makes an authenticated request
    resp = await client.get(
        f"/topics/{topic.id}",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert resp.status_code == 200

    await session.refresh(transfer)
    assert transfer.status == TransferStatus.denied


@pytest.mark.anyio
async def test_execute_transfer_swaps_roles(session, topic_with_creator):
    topic, creator, _ = topic_with_creator

    admin = Member(topic_id=topic.id, role=MemberRole.admin, email="admin@test.com")
    session.add(admin)
    await session.flush()

    transfer = CreatorTransfer(
        topic_id=topic.id,
        requested_by_member_id=admin.id,
        deadline=datetime.now(UTC) - timedelta(hours=1),  # Already past
    )
    session.add(transfer)
    await session.commit()

    await execute_transfer(session, transfer.id)
    await session.commit()

    await session.refresh(creator)
    await session.refresh(admin)

    assert creator.role == MemberRole.admin
    assert admin.role == MemberRole.creator
    assert transfer.status == TransferStatus.expired
