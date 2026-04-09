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

import logging
from datetime import UTC, datetime, timedelta

from sqlmodel import select

from app.config import get_settings
from app.db.session import async_session_factory
from app.models.enums import MemberRole, TopicStatus, TransferStatus
from app.models.member import Member
from app.models.token import Token
from app.models.topic import Topic
from app.models.transfer import CreatorTransfer
from app.services.purge import purge_emails
from app.services.transfer import execute_transfer

logger = logging.getLogger(__name__)


async def auto_archive_task() -> None:
    """Archive topics with no activity in the configured number of days."""
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(days=settings.auto_archive_days)

    async with async_session_factory() as session:
        result = await session.execute(
            select(Topic).where(
                Topic.status == TopicStatus.active,
            )
        )
        topics = result.scalars().all()

        for topic in topics:
            # Check if any token has been used recently
            result = await session.execute(
                select(Token).join(Member, Token.member_id == Member.id).where(
                    Member.topic_id == topic.id,
                    Token.last_used_at.is_not(None),  # type: ignore[union-attr]
                    Token.last_used_at > cutoff,
                )
            )
            if result.scalars().first() is not None:
                continue

            logger.info("Auto-archiving topic %s", topic.id)
            topic.status = TopicStatus.archived
            topic.closed_at = datetime.now(UTC)
            session.add(topic)
            await purge_emails(session, topic.id)

        await session.commit()


async def transfer_deadline_task() -> None:
    """Execute transfers past their deadline where creator has not authenticated."""
    async with async_session_factory() as session:
        now = datetime.now(UTC)
        result = await session.execute(
            select(CreatorTransfer).where(
                CreatorTransfer.status == TransferStatus.pending,
                CreatorTransfer.deadline <= now,
            )
        )
        transfers = result.scalars().all()

        for transfer in transfers:
            # Check if creator has been active since transfer was requested
            result = await session.execute(
                select(Member).where(
                    Member.topic_id == transfer.topic_id,
                    Member.role == MemberRole.owner,
                )
            )
            creator = result.scalar_one_or_none()
            if creator is None:
                continue

            result = await session.execute(
                select(Token).where(
                    Token.member_id == creator.id,
                    Token.last_used_at.is_not(None),  # type: ignore[union-attr]
                    Token.last_used_at > transfer.created_at,
                )
            )
            if result.scalars().first() is not None:
                # Creator was active, cancel transfer
                transfer.status = TransferStatus.denied
                transfer.resolved_at = now
                session.add(transfer)
                continue

            logger.info("Executing transfer %s for topic %s", transfer.id, transfer.topic_id)
            try:
                await execute_transfer(session, transfer.id)
            except ValueError as e:
                logger.error("Failed to execute transfer %s: %s", transfer.id, e)

        await session.commit()
