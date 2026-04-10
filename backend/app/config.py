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
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings

# Resolve .env from the project root (two levels above this file: app/ -> backend/ -> project root)
_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    # Core
    database_url: str = "sqlite+aiosqlite:///./weft.db"
    secret_key: str = ""
    base_url: str = "http://localhost:5173"
    creator_transfer_deadline_hours: int = 24
    auto_archive_days: int = 30
    topic_creation_rate_limit: str = "10/hour"

    # Email provider selection: "resend" | "mailgun" | "ses"
    email_provider: str = "resend"

    # SMS provider selection: "twilio" | "sns"
    sms_provider: str = "twilio"

    # Resend
    resend_api_key: str = ""

    # Mailgun
    mailgun_api_key: str = ""
    mailgun_domain: str = ""

    # Amazon SES / SNS shared credentials
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"

    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    # SNS
    sns_sender_id: str = "Weft"

    # Shared from-address for email providers
    email_from_address: str = "Weft <noreply@weft.app>"

    # Attachment storage: "local" | "s3"
    attachment_storage: str = "local"
    attachment_local_path: str = "./attachments"
    attachment_s3_bucket: str = ""
    attachment_s3_prefix: str = "attachments/"
    # Max attachment size in bytes (default 10 MB)
    attachment_max_size_bytes: int = 10 * 1024 * 1024

    model_config = {"env_file": str(_ENV_FILE), "env_file_encoding": "utf-8"}

    @model_validator(mode="after")
    def validate_secret_key(self) -> "Settings":
        if not self.secret_key or self.secret_key == "change-me":
            raise ValueError(
                "SECRET_KEY must be set to a non-empty, non-default value. "
                'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
