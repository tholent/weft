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

"""Shared HTTP error response descriptions for router decorators.

Usage::

    from app.routers._responses import ERR_400, ERR_401, ERR_403, ERR_404

    @router.get("/resource", responses={**ERR_401, **ERR_403, **ERR_404})
    async def get_resource(...): ...
"""

from typing import Any

ERR_400: dict[int | str, dict[str, Any]] = {400: {"description": "Invalid request"}}
ERR_401: dict[int | str, dict[str, Any]] = {401: {"description": "Authentication required"}}
ERR_403: dict[int | str, dict[str, Any]] = {403: {"description": "Insufficient permissions"}}
ERR_404: dict[int | str, dict[str, Any]] = {404: {"description": "Resource not found"}}
ERR_409: dict[int | str, dict[str, Any]] = {409: {"description": "Conflict with current state"}}
ERR_413: dict[int | str, dict[str, Any]] = {413: {"description": "Payload too large"}}
ERR_429: dict[int | str, dict[str, Any]] = {429: {"description": "Rate limit exceeded"}}
