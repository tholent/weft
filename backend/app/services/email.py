import asyncio
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


async def send_invite_email(to_email: str, topic_title: str, magic_link: str) -> None:
    settings = get_settings()
    if not settings.resend_api_key:
        logger.info(
            "DEV MODE — invite email to %s for topic '%s': %s",
            to_email,
            topic_title,
            magic_link,
        )
        return

    import resend

    resend.api_key = settings.resend_api_key
    await asyncio.to_thread(
        resend.Emails.send,
        {
            "from": "Weft <noreply@weft.app>",
            "to": [to_email],
            "subject": f"You've been invited to follow: {topic_title}",
            "html": f'<p>You\'ve been invited to follow updates on "{topic_title}".</p>'
            f'<p><a href="{magic_link}">Click here to view updates</a></p>',
        },
    )


async def send_transfer_notification(
    to_email: str, topic_title: str, deadline: str
) -> None:
    settings = get_settings()
    if not settings.resend_api_key:
        logger.info(
            "DEV MODE — transfer notification to %s for topic '%s', deadline: %s",
            to_email,
            topic_title,
            deadline,
        )
        return

    import resend

    resend.api_key = settings.resend_api_key
    await asyncio.to_thread(
        resend.Emails.send,
        {
            "from": "Weft <noreply@weft.app>",
            "to": [to_email],
            "subject": f"Creator transfer requested for: {topic_title}",
            "html": f"<p>A creator transfer has been requested for \"{topic_title}\".</p>"
            f"<p>If you do not visit the topic before {deadline}, "
            f"your creator role will be transferred.</p>",
        },
    )


async def send_transfer_complete_notification(
    to_emails: list[str], topic_title: str
) -> None:
    settings = get_settings()
    if not settings.resend_api_key:
        logger.info(
            "DEV MODE — transfer complete notification to %s for topic '%s'",
            to_emails,
            topic_title,
        )
        return

    import resend

    resend.api_key = settings.resend_api_key

    def _send_all():
        for email in to_emails:
            resend.Emails.send(
                {
                    "from": "Weft <noreply@weft.app>",
                    "to": [email],
                    "subject": f"Creator transfer completed for: {topic_title}",
                    "html": f'<p>The creator role for "{topic_title}" has been transferred.</p>',
                }
            )

    await asyncio.to_thread(_send_all)
