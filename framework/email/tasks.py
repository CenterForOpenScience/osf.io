import smtplib
import logging
from email.mime.text import MIMEText

from framework.celery_tasks import app
from framework.sentry import sentry
from website import settings
import sendgrid

logger = logging.getLogger(__name__)


@app.task
def send_email(from_addr, to_addr, subject, message, mimetype='html', ttls=True, login=True,
                username=None, password=None, categories=None, attachment_name=None, attachment_content=None):
    """Send email to specified destination.
    Email is sent from the email specified in FROM_EMAIL settings in the
    settings module.

    Uses the Sendgrid API if ``settings.SENDGRID_API_KEY`` is set.

    :param from_addr: A string, the sender email
    :param to_addr: A string, the recipient
    :param subject: subject of email
    :param message: body of message
    :param tuple categories: Categories to add to the email using SendGrid's
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
            mimetype=mimetype,
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
            mimetype=mimetype,
            ttls=ttls,
            login=login,
            username=username,
            password=password
        )


def _send_with_smtp(from_addr, to_addr, subject, message, mimetype='html', ttls=True, login=True, username=None, password=None):
    username = username or settings.MAIL_USERNAME
    password = password or settings.MAIL_PASSWORD

    if login and (username is None or password is None):
        logger.error('Mail username and password not set; skipping send.')
        return

    msg = MIMEText(message, mimetype, _charset='utf-8')
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
        msg=msg.as_string()
    )
    s.quit()
    return True


def _send_with_sendgrid(from_addr, to_addr, subject, message, mimetype='html', categories=None, attachment_name=None, attachment_content=None, client=None):
    if (settings.SENDGRID_WHITELIST_MODE and to_addr in settings.SENDGRID_EMAIL_WHITELIST) or settings.SENDGRID_WHITELIST_MODE is False:
        client = client or sendgrid.SendGridClient(settings.SENDGRID_API_KEY)
        mail = sendgrid.Mail()
        mail.set_from(from_addr)
        mail.add_to(to_addr)
        mail.set_subject(subject)
        if mimetype == 'html':
            mail.set_html(message)
        else:
            mail.set_text(message)
        if categories:
            mail.set_categories(categories)
        if attachment_name and attachment_content:
            mail.add_attachment_stream(attachment_name, attachment_content)

        status, msg = client.send(mail)
        return status < 400
    else:
        sentry.log_message(
            'SENDGRID_WHITELIST_MODE is True. Failed to send emails to non-whitelisted recipient {}.'.format(to_addr)
        )
