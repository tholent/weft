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

"""Attachment service for photo file storage and retrieval."""

import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import get_settings
from app.models.attachment import Attachment

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

_CONTENT_TYPE_EXT: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}


async def save_attachment(
    session: AsyncSession,
    update_id: uuid.UUID,
    topic_id: uuid.UUID,
    filename: str,
    content_type: str,
    data: bytes,
) -> Attachment:
    """Validate and persist an uploaded photo attachment.

    Files are stored at:
        {attachment_storage_path}/{topic_id}/{update_id}/{attachment_id}.{ext}

    Raises:
        ValueError: If the content type is not allowed or the file exceeds the size limit.
    """
    settings = get_settings()

    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(
            f"Unsupported content type '{content_type}'. "
            f"Allowed types: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}"
        )

    if len(data) > settings.attachment_max_size_bytes:
        max_mb = settings.attachment_max_size_bytes / (1024 * 1024)
        raise ValueError(
            f"File size {len(data)} bytes exceeds maximum allowed size of {max_mb:.0f} MB"
        )

    attachment_id = uuid.uuid4()
    ext = _CONTENT_TYPE_EXT.get(content_type, "bin")
    storage_key = f"{topic_id}/{update_id}/{attachment_id}.{ext}"

    # Write to local disk
    storage_root = Path(settings.attachment_local_path)
    dest = storage_root / str(topic_id) / str(update_id)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"{attachment_id}.{ext}").write_bytes(data)

    attachment = Attachment(
        id=attachment_id,
        update_id=update_id,
        topic_id=topic_id,
        filename=filename,
        content_type=content_type,
        storage_key=storage_key,
        size_bytes=len(data),
    )
    session.add(attachment)
    await session.flush()
    return attachment


async def get_attachments(
    session: AsyncSession,
    update_id: uuid.UUID,
) -> list[Attachment]:
    """Return all attachments for a given update, ordered by creation time."""
    result = await session.execute(
        select(Attachment).where(Attachment.update_id == update_id).order_by(Attachment.created_at)
    )
    return list(result.scalars().all())


async def get_attachment(
    session: AsyncSession,
    attachment_id: uuid.UUID,
) -> Attachment | None:
    """Return a single attachment by ID, or None if not found."""
    result = await session.execute(select(Attachment).where(Attachment.id == attachment_id))
    return result.scalar_one_or_none()


def get_attachment_path(attachment: Attachment) -> Path:
    """Resolve the local filesystem path for an attachment's stored file."""
    settings = get_settings()
    return Path(settings.attachment_local_path) / attachment.storage_key
