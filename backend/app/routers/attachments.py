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

"""Attachment upload and serve endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.deps import require_topic_admin, require_topic_member
from app.models.member import Member
from app.schemas.attachment import AttachmentResponse
from app.services.attachment import (
    get_attachment,
    get_attachment_path,
    get_attachments,
    save_attachment,
)

router = APIRouter(prefix="/topics/{topic_id}", tags=["attachments"])


@router.post(
    "/updates/{update_id}/attachments",
    response_model=AttachmentResponse,
    status_code=201,
)
async def upload_attachment(
    topic_id: uuid.UUID,
    update_id: uuid.UUID,
    file: UploadFile,
    member: Member = Depends(require_topic_admin),
    session: AsyncSession = Depends(get_session),
) -> AttachmentResponse:
    """Upload a photo attachment for an update.  Admin+ only.

    Accepts multipart/form-data with a single ``file`` field.
    Allowed content types: image/jpeg, image/png, image/webp, image/gif.
    """
    if file.content_type is None:
        raise HTTPException(status_code=400, detail="Missing content type")

    data = await file.read()
    try:
        attachment = await save_attachment(
            session,
            update_id=update_id,
            topic_id=topic_id,
            filename=file.filename or "upload",
            content_type=file.content_type,
            data=data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return AttachmentResponse(
        id=attachment.id,
        update_id=attachment.update_id,
        topic_id=attachment.topic_id,
        filename=attachment.filename,
        content_type=attachment.content_type,
        size_bytes=attachment.size_bytes,
        created_at=attachment.created_at,
    )


@router.get("/updates/{update_id}/attachments", response_model=list[AttachmentResponse])
async def list_attachments(
    topic_id: uuid.UUID,
    update_id: uuid.UUID,
    member: Member = Depends(require_topic_member),
    session: AsyncSession = Depends(get_session),
) -> list[AttachmentResponse]:
    """List all attachments for an update."""
    attachments = await get_attachments(session, update_id)
    return [
        AttachmentResponse(
            id=a.id,
            update_id=a.update_id,
            topic_id=a.topic_id,
            filename=a.filename,
            content_type=a.content_type,
            size_bytes=a.size_bytes,
            created_at=a.created_at,
        )
        for a in attachments
    ]


@router.get("/attachments/{attachment_id}")
async def serve_attachment(
    topic_id: uuid.UUID,
    attachment_id: uuid.UUID,
    member: Member = Depends(require_topic_member),
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    """Serve the raw file for an attachment.

    The attachment must belong to the authenticated member's topic.
    """
    attachment = await get_attachment(session, attachment_id)
    if attachment is None or attachment.topic_id != topic_id:
        raise HTTPException(status_code=404, detail="Attachment not found")

    path = get_attachment_path(attachment)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Attachment file not found on disk")

    return FileResponse(
        path=str(path),
        media_type=attachment.content_type,
        filename=attachment.filename,
    )
