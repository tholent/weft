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

"""Topic export endpoint.

Returns a privacy-safe JSON snapshot of a topic.  Only the topic owner
may trigger an export.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.deps import require_topic_owner
from app.models.member import Member
from app.services.export import export_topic

router = APIRouter(prefix="/topics", tags=["export"])


@router.get("/{topic_id}/export")
async def export_topic_endpoint(
    topic_id: uuid.UUID,
    member: Member = Depends(require_topic_owner),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Export the full topic as a privacy-safe JSON document.

    Owner only.  The response is a downloadable JSON file.
    """
    try:
        data: dict[str, Any] = await export_topic(session, topic_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f'attachment; filename="weft-export-{topic_id}.json"',
        },
    )
