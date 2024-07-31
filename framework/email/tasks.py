import logging
import smtplib
from base64 import b64encode
from email.mime.text import MIMEText
from io import BytesIO

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Attachment, Mail, FileContent, Category

from framework import sentry
from framework.celery_tasks import app
from website import settings

logger = logging.getLogger(__name__)


@app.task
def send_email(
    from_addr: str,
    to_addr: str,
    subject: str,
    message: str,
    ttls: bool = True,
    login: bool = True,
    username: str = None,
    password: str = None,
    categories=None,
    attachment_name: str = None,
    attachment_content: str | bytes | BytesIO = None,
):
    """Send email to specified destination.
    Email is sent from the email specified in FROM_EMAIL settings in the
    settings module.

    Uses the Sendgrid API if ``settings.SENDGRID_API_KEY`` is set.

    :param from_addr: A string, the sender email
    :param to_addr: A string, the recipient
    :param subject: subject of email
    :param message: body of message
    :param categories: Categories to add to the email using SendGrid's
        SMTPAPI. Used for email analytics.
        See https://sendgrid.com/docs/User_Guide/Statistics/categories.html
        This parameter is only respected if using the Sendgrid API.
        ``settings.SENDGRID_API_KEY`` must be set.

    :return: True if successful
    """
    if not settings.USE_EMAIL:
        return
    if settings.SENDGRID_API_KEY:
        return _send_with_sendgrid(
            from_addr=from_addr,
            to_addr=to_addr,
            subject=subject,
            message=message,
            categories=categories,
            attachment_name=attachment_name,
            attachment_content=attachment_content,
        )
    else:
        return _send_with_smtp(
            from_addr=from_addr,
            to_addr=to_addr,
            subject=subject,
            message=message,
            ttls=ttls,
            login=login,
            username=username,
            password=password,
        )


def _send_with_smtp(from_addr, to_addr, subject, message, ttls=True, login=True, username=None, password=None):
    username = username or settings.MAIL_USERNAME
    password = password or settings.MAIL_PASSWORD

    if login and (username is None or password is None):
        logger.error('Mail username and password not set; skipping send.')
        return

    msg = MIMEText(message, 'html', _charset='utf-8')
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_addr

    s = smtplib.SMTP(settings.MAIL_SERVER)
    s.ehlo()
    if ttls:
        s.starttls()
        s.ehlo()
    if login:
        s.login(username, password)
    s.sendmail(
        from_addr=from_addr,
        to_addrs=[to_addr],
        msg=msg.as_string(),
    )
    s.quit()
    return True


def _send_with_sendgrid(
    from_addr: str,
    to_addr: str,
    subject: str,
    message: str,
    categories=None,
    attachment_name: str = None,
    attachment_content=None,
    client=None,
):
    if (
        settings.SENDGRID_WHITELIST_MODE and to_addr in settings.SENDGRID_EMAIL_WHITELIST
    ) or settings.SENDGRID_WHITELIST_MODE is False:
        client = client or SendGridAPIClient(settings.SENDGRID_API_KEY)
        mail = Mail(from_email=from_addr, html_content=message, to_emails=to_addr, subject=subject)
        if categories:
            mail.category = [Category(x) for x in categories]
        if attachment_name and attachment_content:
            content_bytes = _content_to_bytes(attachment_content)
            content_bytes = FileContent(b64encode(content_bytes).decode())
            attachment = Attachment(file_content=content_bytes, file_name=attachment_name)
            mail.add_attachment(attachment)

        response = client.send(mail)
        if response.status_code >= 400:
            sentry.log_message(
                f'{response.status_code} error response from sendgrid.'
                f'from_addr:  {from_addr}\n'
                f'to_addr:  {to_addr}\n'
                f'subject:  {subject}\n'
                'mimetype:  html\n'
                f'message:  {response.body[:30]}\n'
                f'categories:  {categories}\n'
                f'attachment_name:  {attachment_name}\n'
            )
        return response.status_code < 400
    else:
        sentry.log_message(
            f'SENDGRID_WHITELIST_MODE is True. Failed to send emails to non-whitelisted recipient {to_addr}.'
        )


def _content_to_bytes(attachment_content: BytesIO | str | bytes) -> bytes:
    if isinstance(attachment_content, bytes):
        return attachment_content
    elif isinstance(attachment_content, BytesIO):
        return attachment_content.getvalue()
    elif isinstance(attachment_content, str):
        return attachment_content.encode()
    else:
        return str(attachment_content).encode()
