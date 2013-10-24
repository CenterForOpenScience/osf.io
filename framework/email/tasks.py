import smtplib
import logging
from email.mime.text import MIMEText

from framework.tasks import celery
from website import settings  # TODO: Use framework's config module instead

logger = logging.getLogger(__name__)


@celery.task
def send_email(from_addr, to_addr, subject, message, mimetype='html', ttls=True, login=True):
    """Send email to specified destination.
    Email is sent from the email specified in FROM_EMAIL settings in the
    settings module.

    :param from_addr: A string, the sender email
    :param to_addr: A string, the recipient
    :param subject: subject of email
    :param message: body of message

    :return: True if successful
    """
    msg = MIMEText(message, mimetype, _charset='utf-8')
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_addr

    s = smtplib.SMTP(settings.mail_server)
    s.ehlo()
    if ttls:
        s.starttls()
        s.ehlo()
    if login:
        s.login(settings.mail_username, settings.mail_password)
    s.sendmail(
        from_addr=from_addr,
        to_addrs=[to_addr],
        msg=msg.as_string()
    )
    s.quit()
    return True
