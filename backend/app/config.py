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

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./weft.db"
    secret_key: str = ""
    resend_api_key: str = ""
    base_url: str = "http://localhost:5173"
    creator_transfer_deadline_hours: int = 24
    auto_archive_days: int = 30
    topic_creation_rate_limit: str = "10/hour"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @model_validator(mode="after")
    def validate_secret_key(self) -> "Settings":
        if not self.secret_key or self.secret_key == "change-me":
            raise ValueError(
                "SECRET_KEY must be set to a non-empty, non-default value. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
