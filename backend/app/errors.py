# Copyright 2026 Chris Wells <chris@tholern.com>
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

"""Application-level exception handlers.

Centralises error response formatting so that the main application module
does not need to import private or unstable library internals.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded


async def rate_limit_exceeded_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a 429 JSON response when a slowapi rate limit is exceeded.

    This replaces the private ``slowapi._rate_limit_exceeded_handler`` import
    with a stable, application-owned handler that preserves the same response
    shape.
    """
    if isinstance(exc, RateLimitExceeded):
        detail = str(exc.detail) if hasattr(exc, "detail") else "Rate limit exceeded"
    else:
        detail = "Rate limit exceeded"
    return JSONResponse({"error": detail}, status_code=429)
