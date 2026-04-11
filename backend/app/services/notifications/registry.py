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

"""Provider registry for runtime notification provider selection."""

from app.models.enums import NotificationChannel
from app.services.notifications.provider import NotificationProvider


class ProviderRegistry:
    """Registry that maps notification channels to their active providers."""

    def __init__(self) -> None:
        self._providers: dict[NotificationChannel, NotificationProvider] = {}

    def register(self, provider: NotificationProvider) -> None:
        """Register a provider. Overwrites any existing provider for its channel."""
        self._providers[provider.channel] = provider

    def get(self, channel: NotificationChannel) -> NotificationProvider | None:
        """Return the provider for *channel*, or None if not registered."""
        return self._providers.get(channel)

    def get_default(self) -> NotificationProvider | None:
        """Return the email provider if registered, otherwise the first registered provider."""
        if NotificationChannel.email in self._providers:
            return self._providers[NotificationChannel.email]
        if self._providers:
            return next(iter(self._providers.values()))
        return None


def create_registry(settings: object) -> ProviderRegistry:
    """Build and return a ProviderRegistry based on application settings.

    Reads ``settings.email_provider`` and ``settings.sms_provider`` to
    instantiate and register the configured providers.  Providers are only
    registered when their required credentials are non-empty.
    """
    from app.config import Settings

    if not isinstance(settings, Settings):
        raise TypeError(f"Expected Settings instance, got {type(settings)}")

    registry = ProviderRegistry()

    # --- Email provider ---
    if settings.email_provider == "resend":
        if settings.resend_api_key:
            from app.services.notifications.resend_provider import ResendEmailProvider

            registry.register(
                ResendEmailProvider(
                    api_key=settings.resend_api_key,
                    from_address=settings.email_from_address,
                )
            )
    elif settings.email_provider == "mailgun":
        if settings.mailgun_api_key and settings.mailgun_domain:
            from app.services.notifications.mailgun_provider import MailgunEmailProvider

            registry.register(
                MailgunEmailProvider(
                    api_key=settings.mailgun_api_key,
                    domain=settings.mailgun_domain,
                    from_address=settings.email_from_address,
                )
            )
    elif settings.email_provider == "ses":
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            from app.services.notifications.ses_provider import SESEmailProvider

            registry.register(
                SESEmailProvider(
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    aws_region=settings.aws_region,
                    from_address=settings.email_from_address,
                )
            )

    # --- SMS provider ---
    if settings.sms_provider == "twilio":
        if (
            settings.twilio_account_sid
            and settings.twilio_auth_token
            and settings.twilio_from_number
        ):
            from app.services.notifications.twilio_provider import TwilioSMSProvider

            registry.register(
                TwilioSMSProvider(
                    account_sid=settings.twilio_account_sid,
                    auth_token=settings.twilio_auth_token,
                    from_number=settings.twilio_from_number,
                )
            )
    elif settings.sms_provider == "sns":
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            from app.services.notifications.sns_provider import SNSSMSProvider

            registry.register(
                SNSSMSProvider(
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    aws_region=settings.aws_region,
                    sender_id=settings.sns_sender_id,
                )
            )
    elif settings.sms_provider == "vonage":
        if settings.vonage_api_key and settings.vonage_api_secret and settings.vonage_from_sender:
            from app.services.notifications.vonage_provider import VonageSMSProvider

            registry.register(
                VonageSMSProvider(
                    api_key=settings.vonage_api_key,
                    api_secret=settings.vonage_api_secret,
                    from_sender=settings.vonage_from_sender,
                )
            )

    return registry
